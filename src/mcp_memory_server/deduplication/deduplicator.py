"""
Main Deduplication Logic for MCP Memory Server

Implements the core deduplication system with batch processing and ingestion-time checking.
Based on the algorithm from docs/memory-deduplication-proposal.md with enhancements.
"""

import time
import logging
from typing import List, Dict, Any, Tuple, Optional
from langchain_core.documents import Document

from .similarity import SimilarityCalculator
from .merger import DocumentMerger


class MemoryDeduplicator:
    """Main deduplication system for the hierarchical memory system."""
    
    def __init__(self, deduplication_config: dict):
        """Initialize deduplication system.
        
        Args:
            deduplication_config: Configuration dict for deduplication settings
        """
        self.config = deduplication_config
        self.enabled = deduplication_config.get('enabled', True)
        self.similarity_threshold = deduplication_config.get('similarity_threshold', 0.95)
        self.min_importance_diff = deduplication_config.get('min_importance_diff', 0.1)
        self.preserve_high_access = deduplication_config.get('preserve_high_access', True)
        self.target_collections = deduplication_config.get('collections', ['short_term', 'long_term'])
        
        # Initialize components
        self.similarity_calculator = SimilarityCalculator(self.similarity_threshold)
        self.document_merger = DocumentMerger()
        
        # Statistics tracking
        self.stats = {
            'total_duplicates_found': 0,
            'total_documents_merged': 0,
            'total_storage_saved': 0,
            'last_deduplication': None,
            'processing_time_total': 0.0
        }
        
        logging.info(f"MemoryDeduplicator initialized with threshold {self.similarity_threshold}")
    
    def check_ingestion_duplicates(self, new_content: str, new_metadata: dict, 
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
            candidates = collection.similarity_search(new_content, k=5)
            
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
            
            # Determine action based on similarity
            if best_similarity > 0.95:
                return 'boost_existing', best_candidate, best_similarity
            elif best_similarity > 0.85:
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
    
    def deduplicate_collection(self, collection, dry_run: bool = False) -> Dict[str, Any]:
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
            all_docs = collection.similarity_search("", k=10000)  # Large number to get all
            
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
            
            # Find duplicates using existing proposal algorithm
            # Note: This is limited without direct embedding access
            # In full implementation, would extract embeddings from ChromaDB
            duplicate_pairs = self._find_duplicates_simple(doc_dicts)
            
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
            'last_check': time.time()
        })
        
        return current_stats
    
    def preview_duplicates(self, collection) -> Dict[str, Any]:
        """Preview potential duplicates without making changes.
        
        Args:
            collection: ChromaDB collection to analyze
            
        Returns:
            Dictionary with duplicate analysis results
        """
        return self.deduplicate_collection(collection, dry_run=True)
    
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