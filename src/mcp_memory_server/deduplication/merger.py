"""
Document Merger for Deduplication

Handles merging duplicate documents while preserving metadata and audit trails.
Based on the metadata merging strategy from docs/memory-deduplication-proposal.md
"""

import time
import json
import logging
from typing import Dict, Any, List, Tuple, Optional


class DocumentMerger:
    """Handles merging of duplicate documents with metadata preservation."""

    def __init__(self, chunk_manager: Any = None) -> None:
        """Initialize document merger.

        Args:
            chunk_manager: ChunkRelationshipManager instance for handling relationships
        """
        self.merge_history: List[Dict[str, Any]] = []
        self.chunk_manager = chunk_manager

    def choose_best_document(self, doc1: Dict[str, Any], doc2: Dict[str, Any]) -> Dict[str, Any]:
        """Choose the best document to keep when merging duplicates.

        Selection criteria from existing proposal:
        1. Higher importance score (primary factor)
        2. More access count (secondary factor)
        3. More recent timestamp (tiebreaker)

        Args:
            doc1: First document dictionary
            doc2: Second document dictionary

        Returns:
            The document dictionary to keep
        """
        # Extract metadata with defaults
        doc1_metadata = doc1.get('metadata', {})
        doc2_metadata = doc2.get('metadata', {})

        # Primary: Importance score
        importance1 = doc1_metadata.get('importance_score', 0.0)
        importance2 = doc2_metadata.get('importance_score', 0.0)

        if importance1 != importance2:
            return doc1 if importance1 > importance2 else doc2

        # Secondary: Access count
        access1 = doc1_metadata.get('access_count', 0)
        access2 = doc2_metadata.get('access_count', 0)

        if access1 != access2:
            return doc1 if access1 > access2 else doc2

        # Tiebreaker: Most recent timestamp
        timestamp1 = doc1_metadata.get('timestamp', 0)
        timestamp2 = doc2_metadata.get('timestamp', 0)

        return doc1 if timestamp1 > timestamp2 else doc2

    def merge_metadata(self, doc1: Dict[str, Any], doc2: Dict[str, Any],
                       similarity_score: float) -> Dict[str, Any]:
        """Merge metadata from two duplicate documents.

        Merging strategy from existing proposal:
        - Keep maximum importance score
        - Sum access counts
        - Keep earliest first_seen timestamp
        - Keep latest last_accessed timestamp
        - Create audit trail of merged documents

        Args:
            doc1: First document dictionary
            doc2: Second document dictionary
            similarity_score: Similarity score between documents

        Returns:
            Merged metadata dictionary
        """
        current_time = time.time()

        metadata1 = doc1.get('metadata', {})
        metadata2 = doc2.get('metadata', {})

        # Determine which document to use as base
        best_doc = self.choose_best_document(doc1, doc2)
        other_doc = doc2 if best_doc == doc1 else doc1

        best_metadata = best_doc.get('metadata', {})

        # Create merged metadata
        merged_metadata = best_metadata.copy()

        # Merge key statistics
        merged_metadata.update({
            # Importance: keep maximum
            'importance_score': max(
                metadata1.get('importance_score', 0.0),
                metadata2.get('importance_score', 0.0)
            ),

            # Access: sum counts
            'access_count': (
                metadata1.get('access_count', 0) +
                metadata2.get('access_count', 0)
            ),

            # Time tracking
            'first_seen': min(
                metadata1.get('timestamp', current_time),
                metadata2.get('timestamp', current_time)
            ),
            'last_accessed': max(
                metadata1.get('last_accessed', current_time),
                metadata2.get('last_accessed', current_time)
            ),

            # Deduplication audit trail
            'duplicate_sources': [
                best_doc.get('id', 'unknown'),
                other_doc.get('id', 'unknown')
            ],
            'merge_timestamp': current_time,
            'similarity_score': similarity_score,
            'deduplication_version': '1.0',

            # Enhanced metadata
            'merged_from_count': 2,
            'content_length': max(
                len(doc1.get('page_content', '')),
                len(doc2.get('page_content', ''))
            ),

            # Preserve important flags
            'permanent_flag': (
                metadata1.get('permanent_flag', False) or
                metadata2.get('permanent_flag', False)
            ),
            'ttl_tier': self._merge_ttl_tiers(
                metadata1.get('ttl_tier'),
                metadata2.get('ttl_tier')
            )
        })

        # Preserve any explicit permanence reasons
        permanence_reasons = []
        if metadata1.get('permanence_reason'):
            permanence_reasons.append(metadata1['permanence_reason'])
        if metadata2.get('permanence_reason'):
            permanence_reasons.append(metadata2['permanence_reason'])
        if permanence_reasons:
            merged_metadata['permanence_reason'] = ', '.join(permanence_reasons)

        return dict(merged_metadata)

    def _merge_ttl_tiers(self, tier1: Optional[str], tier2: Optional[str]) -> str:
        """Merge TTL tiers, choosing the more permanent one."""
        if not tier1:
            return tier2 or 'medium_frequency'
        if not tier2:
            return tier1

        # Order from least to most permanent
        tier_order = {
            'high_frequency': 0,
            'medium_frequency': 1,
            'low_frequency': 2,
            'static': 3,
            'permanent': 4
        }

        order1 = tier_order.get(tier1, 1)
        order2 = tier_order.get(tier2, 1)

        return tier1 if order1 >= order2 else tier2

    def create_merged_document(self, doc1: Dict[str, Any], doc2: Dict[str, Any],
                               similarity_score: float) -> Dict[str, Any]:
        """Create a merged document from two duplicates.

        Args:
            doc1: First document dictionary
            doc2: Second document dictionary
            similarity_score: Similarity score between documents

        Returns:
            New merged document dictionary
        """
        # Choose best document as base
        best_doc = self.choose_best_document(doc1, doc2)

        # Merge metadata
        merged_metadata = self.merge_metadata(doc1, doc2, similarity_score)

        # Create merged document
        merged_doc = {
            'id': best_doc.get('id', f"merged_{int(time.time() * 1000)}"),
            'page_content': best_doc.get('page_content', ''),
            'metadata': merged_metadata,
            'embedding': best_doc.get('embedding')  # Keep best document's embedding
        }

        # Record merge operation
        merge_record = {
            'timestamp': time.time(),
            'merged_doc_id': merged_doc['id'],
            'source_doc_ids': [
                doc1.get('id', 'unknown'),
                doc2.get('id', 'unknown')
            ],
            'similarity_score': similarity_score,
            'chosen_source': best_doc.get('id', 'unknown'),
            'merge_reason': 'duplicate_detected'
        }
        self.merge_history.append(merge_record)

        logging.info(f"Merged duplicate documents with similarity {similarity_score:.3f}")

        return merged_doc

    def batch_merge_duplicates(self, duplicate_pairs: List[Tuple[Dict, Dict, float]]) -> List[Dict[str, Any]]:
        """Process multiple duplicate pairs and create merged documents.

        Args:
            duplicate_pairs: List of (doc1, doc2, similarity) tuples

        Returns:
            List of merged documents
        """
        if not duplicate_pairs:
            return []

        merged_documents = []
        processed_docs = set()

        for doc1, doc2, similarity in duplicate_pairs:
            doc1_id = doc1.get('id', str(hash(doc1.get('page_content', ''))))
            doc2_id = doc2.get('id', str(hash(doc2.get('page_content', ''))))

            # Skip if either document was already processed
            if doc1_id in processed_docs or doc2_id in processed_docs:
                continue

            # Create merged document
            merged_doc = self.create_merged_document(doc1, doc2, similarity)
            merged_documents.append(merged_doc)

            # Mark both source documents as processed
            processed_docs.add(doc1_id)
            processed_docs.add(doc2_id)

        logging.info(
            f"Batch merge completed: {
                len(merged_documents)} merged documents from {
                len(duplicate_pairs)} duplicate pairs")

        return merged_documents

    def get_merge_statistics(self) -> Dict[str, Any]:
        """Get statistics about merge operations performed.

        Returns:
            Dictionary with merge statistics
        """
        if not self.merge_history:
            return {
                'total_merges': 0,
                'average_similarity': 0.0,
                'recent_merges': 0
            }

        current_time = time.time()
        recent_cutoff = current_time - 86400  # 24 hours ago

        similarities = [record['similarity_score'] for record in self.merge_history]
        recent_merges = [r for r in self.merge_history if r['timestamp'] > recent_cutoff]

        return {
            'total_merges': len(self.merge_history),
            'average_similarity': sum(similarities) / len(similarities),
            'max_similarity': max(similarities),
            'min_similarity': min(similarities),
            'recent_merges': len(recent_merges),
            'documents_deduplicated': len(self.merge_history) * 2,  # Each merge removes 2 documents
            'first_merge': self.merge_history[0]['timestamp'] if self.merge_history else None,
            'last_merge': self.merge_history[-1]['timestamp'] if self.merge_history else None
        }

    def export_merge_history(self, filepath: str) -> None:
        """Export merge history to file for audit purposes.

        Args:
            filepath: Path to save merge history
        """
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    'merge_history': self.merge_history,
                    'statistics': self.get_merge_statistics(),
                    'exported_at': time.time()
                }, f, indent=2)
            logging.info(f"Merge history exported to {filepath}")
        except Exception as e:
            logging.error(f"Failed to export merge history: {e}")

    def merge_documents_with_relationships(self, primary_doc: Dict[str, Any],
                                           duplicate_docs: List[Dict[str, Any]],
                                           similarity_scores: List[float]) -> Dict[str, Any]:
        """Merge documents while preserving chunk relationships.

        Args:
            primary_doc: Primary document to keep
            duplicate_docs: List of duplicate documents to merge
            similarity_scores: Similarity scores for each duplicate

        Returns:
            Merge summary with relationship information
        """
        current_time = time.time()

        # Extract document IDs for relationship tracking
        primary_doc_id = self._extract_document_id(primary_doc)
        duplicate_doc_ids = [self._extract_document_id(doc) for doc in duplicate_docs]

        # Handle chunk relationships if chunk manager is available
        relationship_summary = {}
        if self.chunk_manager:
            try:
                relationship_summary = self.chunk_manager.handle_deduplication_merge(
                    primary_doc_id=primary_doc_id,
                    merged_doc_ids=duplicate_doc_ids,
                    similarity_scores=similarity_scores
                )
            except Exception as e:
                logging.warning(f"Failed to handle chunk relationships during merge: {e}")
                relationship_summary = {'error': str(e)}

        # Perform traditional metadata merging
        merged_metadata = primary_doc.get('metadata', {}).copy()

        # Aggregate statistics from all duplicates
        total_access_count = merged_metadata.get('access_count', 0)
        max_importance = merged_metadata.get('importance_score', 0.0)
        earliest_timestamp = merged_metadata.get('timestamp', current_time)
        latest_access = merged_metadata.get('last_accessed', current_time)

        for i, duplicate_doc in enumerate(duplicate_docs):
            dup_metadata = duplicate_doc.get('metadata', {})

            total_access_count += dup_metadata.get('access_count', 0)
            max_importance = max(max_importance, dup_metadata.get('importance_score', 0.0))
            earliest_timestamp = min(earliest_timestamp, dup_metadata.get('timestamp', current_time))
            latest_access = max(latest_access, dup_metadata.get('last_accessed', current_time))

        # Update merged metadata with aggregated values
        merged_metadata.update({
            'access_count': total_access_count,
            'importance_score': max_importance,
            'first_seen': earliest_timestamp,
            'last_accessed': latest_access,
            'duplicate_sources': [primary_doc_id] + duplicate_doc_ids,
            'merge_timestamp': current_time,
            'merged_from_count': len(duplicate_docs) + 1,
            'average_similarity': sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0,
            'deduplication_version': '2.0',
            'chunk_relationships_preserved': relationship_summary.get('relationships_preserved', 0)
        })

        # Record comprehensive merge history
        comprehensive_merge_record = {
            'timestamp': current_time,
            'primary_document_id': primary_doc_id,
            'merged_document_ids': duplicate_doc_ids,
            'similarity_scores': dict(zip(duplicate_doc_ids, similarity_scores)),
            'documents_merged': len(duplicate_docs),
            'chunk_relationships': relationship_summary,
            'merge_reason': 'batch_deduplication_with_relationships'
        }
        self.merge_history.append(comprehensive_merge_record)

        return {
            'success': True,
            'primary_document_id': primary_doc_id,
            'merged_count': len(duplicate_docs),
            'merged_metadata': merged_metadata,
            'relationship_summary': relationship_summary,
            'processing_time': time.time() - current_time
        }

    def _extract_document_id(self, doc: Dict[str, Any]) -> str:
        """Extract document ID from document dictionary."""
        # Try multiple possible locations for document ID
        doc_id = (
            doc.get('id') or
            doc.get('metadata', {}).get('document_id') or
            doc.get('metadata', {}).get('chunk_id', '').split('_chunk_')[0] or
            f"unknown_{int(time.time() * 1000)}"
        )
        return doc_id
