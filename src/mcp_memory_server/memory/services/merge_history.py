"""
Merge History Service

Manages document merge history for deduplication tracking.
Handles:
- Loading merge history from system document on startup
- Saving merge history with size limits
- Recording new merges during deduplication
"""

import time
import logging
from typing import Dict, Any, List

from .relationship_persistence import (
    RelationshipPersistenceService,
    SYSTEM_DOC_TYPE_MERGE_HISTORY,
    MAX_MERGE_HISTORY_SIZE,
)


class MergeHistoryService:
    """Service for managing document merge history.

    Merge history tracks which documents were merged during deduplication,
    preserving lineage information for context-aware retrieval.
    """

    def __init__(
        self,
        persistence_service: RelationshipPersistenceService,
        chunk_relationships: Dict[str, Any],
        document_relationships: Dict[str, Any]
    ):
        """Initialize the merge history service.

        Args:
            persistence_service: Service for persisting data to ChromaDB
            chunk_relationships: Reference to chunk relationships dict (shared state)
            document_relationships: Reference to document relationships dict (shared state)
        """
        self.persistence_service = persistence_service
        self.chunk_relationships = chunk_relationships
        self.document_relationships = document_relationships

        # Merge history storage
        self.merge_history: Dict[str, Any] = {}
        self._merge_history_loaded = False

    def load_from_storage(self) -> None:
        """Load merge history from the system document.

        Called on startup to restore merge history from durable storage.
        """
        if self._merge_history_loaded:
            return

        try:
            system_doc = self.persistence_service.get_system_document(
                SYSTEM_DOC_TYPE_MERGE_HISTORY
            )
            if system_doc and system_doc.get('data'):
                self.merge_history = system_doc['data']
                logging.info(
                    f"Loaded {len(self.merge_history)} merge history records from storage"
                )
            else:
                self.merge_history = {}
                logging.debug("No merge history found in storage (first run or empty)")
        except Exception as e:
            logging.warning(f"Failed to load merge history from storage: {e}")
            self.merge_history = {}

        self._merge_history_loaded = True

    def save_to_storage(self) -> bool:
        """Save merge history to the system document.

        Applies size limits to prevent unbounded growth.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Prune old entries if over limit
            if len(self.merge_history) > MAX_MERGE_HISTORY_SIZE:
                sorted_keys = sorted(
                    self.merge_history.keys(),
                    key=lambda k: self.merge_history[k].get('timestamp', 0),
                    reverse=True
                )
                keys_to_keep = sorted_keys[:MAX_MERGE_HISTORY_SIZE]
                self.merge_history = {k: self.merge_history[k] for k in keys_to_keep}
                logging.info(f"Pruned merge history to {MAX_MERGE_HISTORY_SIZE} records")

            return self.persistence_service.save_system_document(
                SYSTEM_DOC_TYPE_MERGE_HISTORY,
                self.merge_history
            )

        except Exception as e:
            logging.error(f"Failed to save merge history to storage: {e}")
            return False

    def ensure_loaded(self) -> None:
        """Ensure merge history is loaded before access."""
        if not self._merge_history_loaded:
            self.load_from_storage()

    def handle_deduplication_merge(
        self,
        primary_doc_id: str,
        merged_doc_ids: List[str],
        similarity_scores: List[float]
    ) -> Dict[str, Any]:
        """Handle chunk relationships when documents are merged during deduplication.

        Args:
            primary_doc_id: ID of the primary (surviving) document
            merged_doc_ids: List of document IDs that were merged
            similarity_scores: Similarity scores for each merged document

        Returns:
            Merge relationship summary
        """
        # Ensure merge history is loaded
        self.ensure_loaded()

        current_time = time.time()
        merge_id = f"merge_{int(current_time * 1000)}"

        # Create merge record
        merge_record: Dict[str, Any] = {
            'merge_id': merge_id,
            'timestamp': current_time,
            'primary_document': primary_doc_id,
            'merged_documents': merged_doc_ids,
            'similarity_scores': dict(zip(merged_doc_ids, similarity_scores)),
            'preserved_relationships': [],
            'consolidated_metadata': {}
        }

        # Update primary document with merge history
        if primary_doc_id in self.document_relationships:
            primary_rel = self.document_relationships[primary_doc_id]
            primary_rel['deduplication_history'].append({
                'merge_id': merge_id,
                'merged_count': len(merged_doc_ids),
                'merge_timestamp': current_time,
                'source_documents': merged_doc_ids.copy()
            })

            # Consolidate relationships from merged documents
            all_related_docs = set(primary_rel.get('related_documents', []))
            consolidated_chunk_count = primary_rel.get('chunk_count', 0)

            for merged_id in merged_doc_ids:
                if merged_id in self.document_relationships:
                    merged_rel = self.document_relationships[merged_id]

                    # Preserve important relationships
                    all_related_docs.update(merged_rel.get('related_documents', []))
                    consolidated_chunk_count += merged_rel.get('chunk_count', 0)

                    # Update chunk relationships to point to primary document
                    for chunk_id in merged_rel.get('chunk_ids', []):
                        if chunk_id in self.chunk_relationships:
                            chunk_rel = self.chunk_relationships[chunk_id]
                            chunk_rel['deduplication_sources'].append({
                                'original_document': merged_id,
                                'merge_timestamp': current_time,
                                'similarity_score': merge_record['similarity_scores'].get(
                                    merged_id, 0.0
                                ),
                                'merged_into': primary_doc_id
                            })

                    # Mark merged document as consolidated
                    merged_rel['consolidated_into'] = primary_doc_id
                    merged_rel['consolidation_timestamp'] = current_time
                    preserved_rels: List[Any] = merge_record['preserved_relationships']
                    preserved_rels.extend(merged_rel.get('related_documents', []))

            # Update primary document relationships
            primary_rel['related_documents'] = list(all_related_docs)
            primary_rel['consolidated_chunk_count'] = consolidated_chunk_count
            primary_rel['merge_benefit_score'] = (
                sum(similarity_scores) / len(similarity_scores)
            )

        # Store merge record
        self.merge_history[merge_id] = merge_record

        # Persist to storage
        self.save_to_storage()

        logging.info(
            f"Handled deduplication merge: {len(merged_doc_ids)} documents "
            f"merged into {primary_doc_id}"
        )

        preserved_list: List[Any] = merge_record.get('preserved_relationships', [])
        return {
            'merge_id': merge_id,
            'documents_merged': len(merged_doc_ids),
            'relationships_preserved': len(preserved_list),
            'average_similarity': (
                sum(similarity_scores) / len(similarity_scores)
                if similarity_scores else 0.0
            )
        }

    def get_merge_related_chunks(
        self,
        source_chunk_id: str,
        document_id: str,
        k_related: int
    ) -> List[Dict[str, Any]]:
        """Get chunks from documents that were merged during deduplication.

        Args:
            source_chunk_id: The source chunk ID
            document_id: The document ID to check for merge history
            k_related: Maximum number of related chunks to return

        Returns:
            List of merge-related chunk information
        """
        merge_related = []

        try:
            if document_id in self.document_relationships:
                doc_rel = self.document_relationships[document_id]

                for merge_info in doc_rel.get('deduplication_history', []):
                    for source_doc_id in merge_info.get('source_documents', []):
                        if source_doc_id in self.document_relationships:
                            source_doc_rel = self.document_relationships[source_doc_id]

                            for chunk_id in source_doc_rel.get('chunk_ids', []):
                                if chunk_id in self.chunk_relationships:
                                    chunk_rel = self.chunk_relationships[chunk_id]
                                    merge_related.append({
                                        'chunk_id': chunk_id,
                                        'document_id': source_doc_id,
                                        'chunk_index': chunk_rel['chunk_index'],
                                        'relationship_type': 'merged_source',
                                        'merge_timestamp': merge_info['merge_timestamp'],
                                        'content_preview': chunk_rel['content_preview'],
                                        'deduplication_sources': chunk_rel[
                                            'deduplication_sources'
                                        ],
                                        'context_relevance': 0.8
                                    })

                                    if len(merge_related) >= k_related:
                                        break

                            if len(merge_related) >= k_related:
                                break

                    if len(merge_related) >= k_related:
                        break

        except Exception as e:
            logging.warning(f"Failed to get merge-related chunks: {e}")

        return merge_related

    def get_statistics(self) -> Dict[str, Any]:
        """Get merge history statistics.

        Returns:
            Dictionary with merge statistics
        """
        self.ensure_loaded()

        return {
            'total_merges': len(self.merge_history),
            'merge_history_loaded': self._merge_history_loaded,
        }
