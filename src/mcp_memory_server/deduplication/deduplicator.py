"""
Main Deduplication Logic for MCP Memory Server

Implements the core deduplication system with batch processing and ingestion-time checking.
Based on the algorithm from docs/memory-deduplication-proposal.md with enhancements.
"""

import time
import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional

from .similarity import SimilarityCalculator
from .merger import DocumentMerger
from .advanced_features import AdvancedDeduplicationFeatures


class MemoryDeduplicator:
    """Main deduplication system for the hierarchical memory system."""

    def __init__(self, deduplication_config: dict, chunk_manager=None):
        """Initialize deduplication system.

        Args:
            deduplication_config: Configuration dict for deduplication settings
            chunk_manager: ChunkRelationshipManager instance for handling relationships
        """
        self.config = deduplication_config
        self.enabled = deduplication_config.get('enabled', True)
        self.similarity_threshold = deduplication_config.get('similarity_threshold', 0.95)
        self.min_importance_diff = deduplication_config.get('min_importance_diff', 0.1)
        self.preserve_high_access = deduplication_config.get('preserve_high_access', True)
        self.target_collections = deduplication_config.get('collections', ['short_term', 'long_term'])

        # Initialize components
        self.similarity_calculator = SimilarityCalculator(self.similarity_threshold)
        self.document_merger = DocumentMerger(chunk_manager)
        self.chunk_manager = chunk_manager
        self.advanced_features = AdvancedDeduplicationFeatures(self, deduplication_config.get('advanced_features', {}))

        # Statistics tracking
        self.stats = {
            'total_duplicates_found': 0,
            'total_documents_merged': 0,
            'total_storage_saved': 0,
            'last_deduplication': None,
            'processing_time_total': 0.0
        }

        logging.info(f"MemoryDeduplicator initialized with threshold {self.similarity_threshold}")

    async def check_ingestion_duplicates(self, new_content: str, new_metadata: dict,
                                         collection) -> Tuple[str, Optional[Dict], float]:
        """Check for duplicates during ingestion to prevent storing redundant content.

        Args:
            new_content: Content of new document
            new_metadata: Metadata of new document
            collection: ChromaDB collection to check against

        Returns:
            Tuple of (action, existing_document, similarity_score)
            Actions: 'add_new', 'boost_existing', 'merge_content'
        """
        if not self.enabled:
            return 'add_new', None, 0.0

        try:
            # Quick similarity search to find candidates
            candidates = await asyncio.to_thread(collection.similarity_search, new_content, k=5)

            if not candidates:
                return 'add_new', None, 0.0

            # Get embeddings for new content (this would need integration with embedding model)
            # For now, use ChromaDB's built-in similarity search results

            best_similarity = 0.0
            best_candidate = None

            for candidate in candidates:
                # Use ChromaDB's similarity search distance as approximation
                # In full implementation, would calculate actual cosine similarity
                candidate_metadata = candidate.metadata

                # Simple content similarity check as fallback
                content_similarity = self._simple_content_similarity(new_content, candidate.page_content)

                if content_similarity > best_similarity:
                    best_similarity = content_similarity
                    best_candidate = {
                        'page_content': candidate.page_content,
                        'metadata': candidate_metadata,
                        'id': candidate_metadata.get('chunk_id', 'unknown')
                    }

            # Apply domain-aware thresholds
            adjusted_thresholds = self.advanced_features.apply_domain_aware_thresholds(
                [{'page_content': new_content, 'metadata': new_metadata}],
                self.similarity_threshold
            )
            domain_threshold, _ = adjusted_thresholds[0] if adjusted_thresholds else (
                self.similarity_threshold, 'default')

            # Determine action based on similarity with domain awareness
            if best_similarity > domain_threshold:
                return 'boost_existing', best_candidate, best_similarity
            elif best_similarity > domain_threshold * 0.85:  # 85% of domain threshold
                return 'merge_content', best_candidate, best_similarity
            else:
                return 'add_new', None, best_similarity

        except Exception as e:
            logging.warning(f"Error during ingestion duplicate check: {e}")
            return 'add_new', None, 0.0

    def _simple_content_similarity(self, content1: str, content2: str) -> float:
        """Simple text similarity calculation as fallback.

        Args:
            content1: First content string
            content2: Second content string

        Returns:
            Simple similarity score (0-1)
        """
        # Normalize content
        c1 = content1.lower().strip()
        c2 = content2.lower().strip()

        # Exact match
        if c1 == c2:
            return 1.0

        # Simple Jaccard similarity on words
        words1 = set(c1.split())
        words2 = set(c2.split())

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    async def deduplicate_collection(self, collection, dry_run: bool = False) -> Dict[str, Any]:
        """Perform batch deduplication on a collection.

        Main algorithm from docs/memory-deduplication-proposal.md

        Args:
            collection: ChromaDB collection to deduplicate
            dry_run: If True, only analyze without making changes

        Returns:
            Dictionary with deduplication results and statistics
        """
        if not self.enabled:
            return {'message': 'Deduplication disabled', 'duplicates_found': 0}

        start_time = time.time()

        try:
            # Get all documents from collection
            # Note: This is a simplified approach. In production, you'd batch process large collections
            all_docs = await asyncio.to_thread(collection.similarity_search, "", k=10000)  # Large number to get all

            if len(all_docs) < 2:
                return {
                    'message': 'Not enough documents for deduplication',
                    'duplicates_found': 0,
                    'documents_processed': len(all_docs)
                }

            # Convert to format expected by similarity calculator
            doc_dicts = []
            for doc in all_docs:
                doc_dict = {
                    'id': doc.metadata.get('chunk_id', str(hash(doc.page_content))),
                    'page_content': doc.page_content,
                    'metadata': doc.metadata,
                    'embedding': None  # Would need to extract from ChromaDB
                }
                doc_dicts.append(doc_dict)

            # Apply semantic clustering if enabled
            clustered_docs = self.advanced_features.perform_semantic_clustering(doc_dicts)

            # Find duplicates using advanced features with domain awareness
            duplicate_pairs = self._find_duplicates_advanced(doc_dicts, clustered_docs)

            if not duplicate_pairs:
                processing_time = time.time() - start_time
                return {
                    'message': 'No duplicates found',
                    'duplicates_found': 0,
                    'documents_processed': len(all_docs),
                    'processing_time': processing_time
                }

            results = {
                'duplicates_found': len(duplicate_pairs),
                'documents_processed': len(all_docs),
                'processing_time': time.time() - start_time,
                'duplicate_pairs': []
            }

            if dry_run:
                # Just return what would be done
                for doc1, doc2, similarity in duplicate_pairs:
                    results['duplicate_pairs'].append({
                        'doc1_id': doc1.get('id'),
                        'doc2_id': doc2.get('id'),
                        'similarity': similarity,
                        'action': 'would_merge',
                        'chosen_doc': self.document_merger.choose_best_document(doc1, doc2).get('id')
                    })
                results['message'] = f'DRY RUN: Found {len(duplicate_pairs)} duplicate pairs'
            else:
                # Actually perform merging
                merged_docs = self.document_merger.batch_merge_duplicates(duplicate_pairs)
                results['merged_documents'] = len(merged_docs)
                results['message'] = f'Merged {len(merged_docs)} duplicate pairs'

                # Update statistics
                self._update_stats(duplicate_pairs, merged_docs)

            return results

        except Exception as e:
            logging.error(f"Error during collection deduplication: {e}")
            return {
                'message': f'Deduplication failed: {str(e)}',
                'duplicates_found': 0,
                'error': str(e)
            }

    def _find_duplicates_simple(self, documents: List[Dict[str, Any]]) -> List[Tuple[Dict, Dict, float]]:
        """Simplified duplicate detection without direct embedding access.

        This is a fallback implementation. Full implementation would use
        the existing proposal's cosine similarity on embeddings.

        Args:
            documents: List of document dictionaries

        Returns:
            List of duplicate pairs with similarity scores
        """
        duplicates = []

        for i, doc1 in enumerate(documents):
            for j, doc2 in enumerate(documents[i + 1:], i + 1):
                # Simple content similarity check
                similarity = self._simple_content_similarity(
                    doc1['page_content'],
                    doc2['page_content']
                )

                if similarity > self.similarity_threshold:
                    duplicates.append((doc1, doc2, similarity))

        return duplicates

    def _find_duplicates_advanced(self, documents: List[Dict[str, Any]],
                                  clustered_docs: Dict[str, Any]) -> List[Tuple[Dict, Dict, float]]:
        """Advanced duplicate detection with domain awareness and semantic clustering.

        Args:
            documents: List of document dictionaries
            clustered_docs: Results from semantic clustering

        Returns:
            List of duplicate pairs with similarity scores
        """
        duplicates = []

        # Apply domain-aware thresholds
        domain_thresholds = self.advanced_features.apply_domain_aware_thresholds(
            documents, self.similarity_threshold
        )

        # Create threshold lookup
        threshold_lookup = {
            doc['id']: threshold for (threshold, reason), doc
            in zip(domain_thresholds, documents)
        }

        # Check within clusters first (more efficient)
        if clustered_docs.get('clusters'):
            for cluster_id, cluster_docs in clustered_docs['clusters'].items():
                cluster_doc_ids = set(cluster_docs)

                # Find duplicates within the cluster
                for i, doc1 in enumerate(documents):
                    if doc1['id'] not in cluster_doc_ids:
                        continue

                    for j, doc2 in enumerate(documents[i + 1:], i + 1):
                        if doc2['id'] not in cluster_doc_ids:
                            continue

                        # Calculate similarity
                        similarity = self._simple_content_similarity(
                            doc1['page_content'], doc2['page_content']
                        )

                        # Use the lower of the two domain thresholds
                        threshold1 = threshold_lookup.get(doc1['id'], self.similarity_threshold)
                        threshold2 = threshold_lookup.get(doc2['id'], self.similarity_threshold)
                        effective_threshold = min(threshold1, threshold2)

                        if similarity > effective_threshold:
                            duplicates.append((doc1, doc2, similarity))
        else:
            # Fallback to simple method if clustering failed
            duplicates = self._find_duplicates_simple(documents)

        # Track advanced features usage
        effectiveness_score = len(duplicates) / len(documents) if len(documents) > 0 else 0.0
        self.advanced_features.track_effectiveness(
            effectiveness_score=effectiveness_score,
            context={
                'total_documents': len(documents),
                'duplicates_found': len(duplicates),
                'clusters_formed': len(clustered_docs.get('clusters', {}))
            }
        )

        return duplicates

    def _update_stats(self, duplicate_pairs: List[Tuple], merged_docs: List[Dict]):
        """Update deduplication statistics.

        Args:
            duplicate_pairs: List of duplicate pairs found
            merged_docs: List of merged documents created
        """
        self.stats['total_duplicates_found'] += len(duplicate_pairs)
        self.stats['total_documents_merged'] += len(merged_docs)
        self.stats['last_deduplication'] = time.time()

        # Estimate storage saved (simplified)
        storage_saved = len(duplicate_pairs) * 2 - len(merged_docs)  # Rough estimate
        self.stats['total_storage_saved'] += storage_saved

    def get_deduplication_stats(self) -> Dict[str, Any]:
        """Get comprehensive deduplication statistics.

        Returns:
            Dictionary with deduplication statistics and health metrics
        """
        current_stats = self.stats.copy()
        current_stats.update({
            'enabled': self.enabled,
            'similarity_threshold': self.similarity_threshold,
            'target_collections': self.target_collections,
            'merger_stats': self.document_merger.get_merge_statistics(),
            'advanced_features_stats': self.advanced_features.get_performance_analytics(),
            'domain_thresholds': self.advanced_features.domain_thresholds,
            'last_check': time.time()
        })

        return current_stats

    async def preview_duplicates(self, collection) -> Dict[str, Any]:
        """Preview potential duplicates without making changes.

        Args:
            collection: ChromaDB collection to analyze

        Returns:
            Dictionary with duplicate analysis results
        """
        return await self.deduplicate_collection(collection, dry_run=True)

    def boost_existing_document(self, existing_doc: Dict[str, Any],
                                new_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Boost importance of existing document when duplicate is detected during ingestion.

        Args:
            existing_doc: Existing document dictionary
            new_metadata: Metadata from new duplicate document

        Returns:
            Updated metadata for existing document
        """
        existing_metadata = existing_doc.get('metadata', {})

        # Boost importance score
        current_importance = existing_metadata.get('importance_score', 0.5)
        new_importance = new_metadata.get('importance_score', 0.5)
        boosted_importance = min(1.0, max(current_importance, new_importance) + 0.05)

        # Increment access count to indicate repeated reference
        access_count = existing_metadata.get('access_count', 0) + 1

        # Update metadata
        updated_metadata = existing_metadata.copy()
        updated_metadata.update({
            'importance_score': boosted_importance,
            'access_count': access_count,
            'last_accessed': time.time(),
            'duplicate_boost_count': existing_metadata.get('duplicate_boost_count', 0) + 1,
            'last_duplicate_detected': time.time()
        })

        logging.info(f"Boosted existing document importance from {current_importance:.3f} to {boosted_importance:.3f}")

        return updated_metadata

    def optimize_thresholds(self) -> Dict[str, Any]:
        """Optimize deduplication thresholds using advanced features.

        Returns:
            Dictionary with optimization results
        """
        return self.advanced_features.optimize_thresholds_automatically()

    def get_domain_analysis(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze documents by domain for threshold recommendations.

        Args:
            documents: List of document dictionaries

        Returns:
            Dictionary with domain analysis results
        """
        # Apply domain classification
        domain_thresholds = self.advanced_features.apply_domain_aware_thresholds(
            documents, self.similarity_threshold
        )

        # Analyze domain distribution
        domain_counts = {}
        for (threshold, reason), doc in zip(domain_thresholds, documents):
            domain = reason.replace('domain_', '') if reason.startswith('domain_') else reason
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return {
            'domain_distribution': domain_counts,
            'threshold_recommendations': {
                domain: threshold for (threshold, reason) in set(domain_thresholds)
                if reason.startswith('domain_')
            },
            'total_documents_analyzed': len(documents)
        }

    def get_clustering_analysis(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform semantic clustering analysis on documents.

        Args:
            documents: List of document dictionaries

        Returns:
            Dictionary with clustering analysis results
        """
        return self.advanced_features.perform_semantic_clustering(documents)

    def get_advanced_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics from advanced features.

        Returns:
            Dictionary with advanced performance analytics
        """
        return self.advanced_features.get_performance_analytics()
