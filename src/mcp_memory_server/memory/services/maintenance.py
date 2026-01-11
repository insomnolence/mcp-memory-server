"""
Memory Maintenance Service

Handles cleanup and memory management operations including:
- Short-term memory maintenance
- Smart cleanup selection with deduplication awareness
- Similarity clustering cleanup
- Age-based cleanup fallback
"""

import time
import logging
import asyncio
from typing import Dict, Any, List, Optional

from langchain_core.documents import Document
from langchain_chroma import Chroma

# Import ChromaDB errors for specific exception handling
try:
    from chromadb.errors import ChromaError
except ImportError:
    ChromaError = Exception

from ..exceptions import MaintenanceError, CleanupError, DeduplicationError


class MemoryMaintenanceService:
    """Service responsible for memory cleanup and maintenance operations."""

    def __init__(
        self,
        short_term_memory: Chroma,
        storage_service,
        deduplicator,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize maintenance service.

        Args:
            short_term_memory: Chroma collection for short-term storage
            storage_service: MemoryStorageService instance for document removal
            deduplicator: MemoryDeduplicator instance
            config: Configuration dictionary
        """
        self.short_term_memory = short_term_memory
        self.storage_service = storage_service
        self.deduplicator = deduplicator

        # Configuration
        config = config or {}
        self.short_term_max_size = config.get('short_term_max_size', 100)

    async def maintain_short_term_memory(self) -> None:
        """Enhanced memory maintenance with deduplication-aware cleanup.

        Triggers when short-term memory exceeds max size.
        """
        try:
            # Get current count
            if hasattr(self.short_term_memory, '_collection'):
                current_count = self.short_term_memory._collection.count()
            else:
                current_count = len(self.short_term_memory.get().get('ids', []))

            if current_count <= self.short_term_max_size:
                return

            # Calculate how many documents to remove
            target_size = int(self.short_term_max_size * 0.8)  # Target 80% capacity
            docs_to_remove = current_count - target_size

            logging.info(
                f"Memory maintenance triggered: {current_count} docs, "
                f"removing {docs_to_remove} to reach {target_size}"
            )

            # Use smart selection for cleanup
            removal_candidates = await self._smart_cleanup_selection(docs_to_remove)

            if removal_candidates:
                self.storage_service.remove_documents_from_collection(
                    self.short_term_memory, removal_candidates
                )
                logging.info(f"Removed {len(removal_candidates)} documents from short-term memory")

        except ChromaError as e:
            logging.warning(f"ChromaDB error during maintenance: {e}")
            raise MaintenanceError(f"Short-term memory maintenance failed: {e}")
        except CleanupError as e:
            logging.warning(f"Cleanup error during maintenance: {e}")
        except Exception as e:
            logging.warning(f"Unexpected maintenance error: {e}")

    async def _smart_cleanup_selection(self, target_removal_count: int) -> List[Document]:
        """Enhanced cleanup selection using deduplication-aware strategies.

        Args:
            target_removal_count: Number of documents to select for removal

        Returns:
            List of Document objects to remove
        """
        all_docs = []
        try:
            # Get all documents with metadata efficiently
            if hasattr(self.short_term_memory, '_collection'):
                chroma_result = self.short_term_memory._collection.get()
                for doc_id, content, metadata in zip(
                    chroma_result.get('ids', []) or [],
                    chroma_result.get('documents', []) or [],
                    chroma_result.get('metadatas', []) or []
                ):
                    # Ensure metadata exists and add the ChromaDB ID for deletion
                    if metadata is None:
                        metadata = {}
                    metadata['chroma_id'] = doc_id
                    all_docs.append(Document(page_content=content or '', metadata=metadata))
            else:
                # Fallback to similarity search if direct access unavailable
                all_docs = self.short_term_memory.similarity_search("", k=1000)

            if len(all_docs) <= target_removal_count:
                return all_docs[:target_removal_count]

            # Phase 1: Remove exact duplicates using deduplication system
            removal_candidates = []
            if self.deduplicator.enabled:
                try:
                    # Find duplicates within the collection (offload to thread)
                    doc_data = [
                        {'content': doc.page_content, 'metadata': doc.metadata, 'document': doc}
                        for doc in all_docs
                    ]
                    duplicates = await asyncio.to_thread(
                        self.deduplicator.similarity_calculator.find_duplicates_batch,
                        doc_data,
                        0.95  # High threshold for exact duplicates
                    )

                    # Add lower-quality duplicates to removal candidates
                    for doc1_data, doc2_data, similarity in duplicates:
                        doc1, doc2 = doc1_data['document'], doc2_data['document']
                        worse_doc = self._choose_worse_document(doc1, doc2)
                        if worse_doc not in removal_candidates:
                            removal_candidates.append(worse_doc)
                            logging.debug(f"Marked duplicate document for removal (similarity: {similarity:.3f})")

                except DeduplicationError as dedup_error:
                    logging.warning(f"Deduplication cleanup failed: {dedup_error}")
                except Exception as dedup_error:
                    logging.warning(f"Unexpected error during deduplication: {dedup_error}")

            # Phase 2: If we still need to remove more, use similarity clustering
            remaining_needed = target_removal_count - len(removal_candidates)
            if remaining_needed > 0:
                remaining_docs = [doc for doc in all_docs if doc not in removal_candidates]
                cluster_removals = await self._similarity_cluster_cleanup(remaining_docs, remaining_needed)
                removal_candidates.extend(cluster_removals)

            # Phase 3: If still need more, fall back to traditional age-based cleanup
            remaining_needed = target_removal_count - len(removal_candidates)
            if remaining_needed > 0:
                remaining_docs = [doc for doc in all_docs if doc not in removal_candidates]
                age_based_removals = self._age_based_cleanup(remaining_docs, remaining_needed)
                removal_candidates.extend(age_based_removals)

            return removal_candidates[:target_removal_count]

        except ChromaError as e:
            logging.warning(f"ChromaDB error during smart cleanup: {e}")
            return self._age_based_cleanup(all_docs, target_removal_count)
        except CleanupError as e:
            logging.warning(f"Cleanup error: {e}")
            return self._age_based_cleanup(all_docs, target_removal_count)
        except Exception as e:
            logging.warning(f"Unexpected smart cleanup error: {e}")
            # Fallback to simple age-based cleanup
            return self._age_based_cleanup(all_docs, target_removal_count)

    def _choose_worse_document(self, doc1: Document, doc2: Document) -> Document:
        """Choose the worse document from a duplicate pair.

        Args:
            doc1: First document
            doc2: Second document

        Returns:
            The document with lower quality score
        """
        def doc_quality_score(doc: Document) -> float:
            metadata = doc.metadata
            return (
                metadata.get('importance_score', 0) * 0.5 +
                metadata.get('access_count', 0) * 0.3 +
                (metadata.get('timestamp', 0) / 86400) * 0.2  # Recency bonus (days)
            )

        return doc1 if doc_quality_score(doc1) < doc_quality_score(doc2) else doc2

    async def _similarity_cluster_cleanup(
        self,
        documents: List[Document],
        target_count: int
    ) -> List[Document]:
        """Find similar document clusters and remove lower-quality documents.

        Args:
            documents: List of documents to analyze
            target_count: Number of documents to select for removal

        Returns:
            List of documents to remove
        """
        if not self.deduplicator.enabled or len(documents) < 2:
            return []

        try:
            # Find similarity clusters at a lower threshold (offload to thread)
            doc_data = [
                {'content': doc.page_content, 'metadata': doc.metadata, 'document': doc}
                for doc in documents
            ]
            similar_pairs = await asyncio.to_thread(
                self.deduplicator.similarity_calculator.find_duplicates_batch,
                doc_data,
                0.75  # Lower threshold for similarity clustering
            )

            # Group similar documents into clusters
            clusters = self._group_into_clusters(similar_pairs)

            removal_candidates = []
            for cluster in clusters:
                if len(cluster) > 1:
                    # Sort cluster by quality, remove all but the best
                    cluster.sort(key=lambda doc: (
                        doc.metadata.get('importance_score', 0) * 0.4 +
                        doc.metadata.get('access_count', 0) * 0.3 +
                        (time.time() - doc.metadata.get('timestamp', 0)) / -86400 * 0.3
                    ), reverse=True)

                    # Add all but the best document to removal candidates
                    for doc in cluster[1:]:
                        age_days = (time.time() - doc.metadata.get('timestamp', 0)) / 86400
                        if age_days > 1:  # Don't remove very recent content
                            removal_candidates.append(doc)
                            if len(removal_candidates) >= target_count:
                                break

                if len(removal_candidates) >= target_count:
                    break

            return removal_candidates[:target_count]

        except Exception as e:
            logging.warning(f"Similarity cluster cleanup failed: {e}")
            return []

    def _group_into_clusters(self, similar_pairs: List[tuple]) -> List[List[Document]]:
        """Group similar document pairs into clusters.

        Args:
            similar_pairs: List of (doc1_data, doc2_data, similarity) tuples

        Returns:
            List of document clusters
        """
        clusters: List[List[Document]] = []
        doc_to_cluster: Dict[int, int] = {}

        for doc1_data, doc2_data, _ in similar_pairs:
            doc1 = doc1_data['document']
            doc2 = doc2_data['document']

            doc1_id = id(doc1)
            doc2_id = id(doc2)

            cluster1_idx = doc_to_cluster.get(doc1_id)
            cluster2_idx = doc_to_cluster.get(doc2_id)

            if cluster1_idx is None and cluster2_idx is None:
                # Both documents are new, create a new cluster
                new_cluster_idx = len(clusters)
                clusters.append([doc1, doc2])
                doc_to_cluster[doc1_id] = new_cluster_idx
                doc_to_cluster[doc2_id] = new_cluster_idx

            elif cluster1_idx is not None and cluster2_idx is None:
                # Add doc2 to doc1's cluster
                clusters[cluster1_idx].append(doc2)
                doc_to_cluster[doc2_id] = cluster1_idx

            elif cluster1_idx is None and cluster2_idx is not None:
                # Add doc1 to doc2's cluster
                clusters[cluster2_idx].append(doc1)
                doc_to_cluster[doc1_id] = cluster2_idx

            elif cluster1_idx != cluster2_idx:
                # Merge the two clusters
                if cluster1_idx is not None and cluster2_idx is not None:
                    # Move all documents from cluster2 to cluster1
                    for doc in clusters[cluster2_idx]:
                        doc_to_cluster[id(doc)] = cluster1_idx
                    clusters[cluster1_idx].extend(clusters[cluster2_idx])
                    clusters[cluster2_idx] = []  # Empty the merged cluster

        # Remove empty clusters
        return [cluster for cluster in clusters if cluster]

    def _age_based_cleanup(self, documents: List[Document], target_count: int) -> List[Document]:
        """Traditional age-based cleanup as fallback.

        Args:
            documents: List of documents to analyze
            target_count: Number of documents to select for removal

        Returns:
            List of documents to remove (oldest/least accessed)
        """
        docs_with_age = []
        for doc in documents:
            timestamp = doc.metadata.get('timestamp', 0)
            access_count = doc.metadata.get('access_count', 0)
            # Prefer removing older and less accessed documents
            priority_score = timestamp + (access_count * 86400)  # Weight access count as days
            docs_with_age.append((priority_score, doc))

        # Sort by priority (lower score = older/less accessed = higher removal priority)
        docs_with_age.sort(key=lambda x: x[0])

        return [doc for _, doc in docs_with_age[:target_count]]
