"""
Chunk Relationship Management with Deduplication Awareness

Tracks relationships between chunks and documents with full deduplication history support.
Enables context-aware retrieval that understands merged documents and related chunks.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.documents import Document


class ChunkRelationshipManager:
    """Manages chunk relationships with deduplication awareness."""
    
    def __init__(self, memory_system, relationship_config: dict = None):
        """Initialize chunk relationship manager.
        
        Args:
            memory_system: Reference to HierarchicalMemorySystem
            relationship_config: Configuration for relationship management
        """
        self.memory_system = memory_system
        self.config = relationship_config or self._get_default_config()
        
        # Relationship tracking
        self.document_relationships = {}  # document_id -> relationship metadata
        self.chunk_relationships = {}     # chunk_id -> relationship metadata
        
        # Deduplication relationship tracking
        self.merge_history = {}          # track document merges and their relationships
        
    def _get_default_config(self) -> dict:
        """Default configuration for chunk relationships."""
        return {
            'enable_related_retrieval': True,
            'max_related_chunks': 3,
            'relationship_decay_days': 30,
            'track_merge_relationships': True,
            'preserve_original_context': True,
            'context_window_size': 2,
            'semantic_relationship_threshold': 0.7,
            'max_relationships_per_chunk': 5,
            'semantic_similarity_threshold': 0.8,
            'co_occurrence_window': 3
        }
    
    def create_document_with_relationships(self, content: str, metadata: dict, 
                                         chunks: List[str], memory_id: str, 
                                         collection_name: str) -> List[Document]:
        """Create documents with enhanced relationship tracking.
        
        Args:
            content: Original document content
            metadata: Document metadata
            chunks: List of content chunks
            memory_id: Unique document ID
            collection_name: Target collection name
            
        Returns:
            List of Document objects with relationship metadata
        """
        current_time = time.time()
        
        # Create document relationship record
        document_relationship = {
            'document_id': memory_id,
            'original_content_length': len(content),
            'chunk_count': len(chunks),
            'creation_time': current_time,
            'collection': collection_name,
            'content_hash': hash(content),
            'language': metadata.get('language', 'text'),
            'source_metadata': metadata.copy(),
            'deduplication_history': [],
            'related_documents': [],
            'chunk_ids': []
        }
        
        # Create enhanced documents with relationship metadata
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{memory_id}_chunk_{i}"
            
            # Enhanced chunk metadata with relationships (flattened for ChromaDB compatibility)
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunks),
                'chunk_id': chunk_id,
                'document_id': memory_id,
                'memory_id': memory_id,  # Add this for test compatibility
                'collection_name': collection_name,  # Add this for test compatibility
                # Note: 'relationships' field removed from ChromaDB metadata - stored in internal relationship manager instead
                # Flatten chunk relationships to simple key-value pairs
                'previous_chunk': f"{memory_id}_chunk_{i-1}" if i > 0 else None,
                'next_chunk': f"{memory_id}_chunk_{i+1}" if i < len(chunks)-1 else None,
                'document_start': i == 0,
                'document_end': i == len(chunks) - 1,
                'relative_position': i / max(len(chunks) - 1, 1),
                'context_start_chunk': max(0, i - self.config['context_window_size']),
                'context_end_chunk': min(len(chunks) - 1, i + self.config['context_window_size']),
                'document_summary': self._generate_document_summary(content),
                'creation_timestamp': current_time,
                'relationship_version': '1.0'
            })
            
            # Store complex relationships separately for internal use
            complex_relationships = {
                'previous_chunk': f"{memory_id}_chunk_{i-1}" if i > 0 else None,
                'next_chunk': f"{memory_id}_chunk_{i+1}" if i < len(chunks)-1 else None,
                'document_start': i == 0,
                'document_end': i == len(chunks) - 1,
                'relative_position': i / max(len(chunks) - 1, 1),
                'context_window': {
                    'start_chunk': max(0, i - self.config['context_window_size']),
                    'end_chunk': min(len(chunks) - 1, i + self.config['context_window_size'])
                }
            }
            
            # Track chunk relationship
            self.chunk_relationships[chunk_id] = {
                'chunk_id': chunk_id,
                'document_id': memory_id,
                'chunk_index': i,
                'content_preview': chunk[:100] + '...' if len(chunk) > 100 else chunk,
                'related_chunks': [],
                'deduplication_sources': [],
                'access_history': [],
                'relationship_strength': {},
                'complex_relationships': complex_relationships  # Store complex metadata here
            }
            
            document_relationship['chunk_ids'].append(chunk_id)
            documents.append(Document(page_content=chunk, metadata=chunk_metadata))
        
        # Store document relationship
        self.document_relationships[memory_id] = document_relationship
        
        # Ensure all chunk relationships are properly stored before proceeding
        for doc in documents:
            chunk_id = doc.metadata.get('chunk_id')
            if chunk_id and chunk_id not in self.chunk_relationships:
                logging.warning(f"Chunk relationship for {chunk_id} was not stored properly, attempting to fix")
                # This should not happen, but if it does, we need to handle it gracefully
        
        # Find and establish semantic relationships with existing documents
        if self.config['enable_related_retrieval']:
            try:
                self._establish_semantic_relationships(memory_id, content, documents)
            except Exception as e:
                logging.warning(f"Failed to establish semantic relationships for {memory_id}: {e}")
        
        return documents
    
    def _generate_document_summary(self, content: str) -> str:
        """Generate a summary of the document for relationship context."""
        # Simple summary - first sentence or first 200 characters
        sentences = content.split('. ')
        if sentences and len(sentences[0]) > 50:
            return sentences[0] + ('.' if not sentences[0].endswith('.') else '')
        else:
            return content[:200] + '...' if len(content) > 200 else content
    
    def _establish_semantic_relationships(self, new_document_id: str, content: str, 
                                        new_documents: List[Document]):
        """Find and establish relationships with semantically similar documents."""
        try:
            # Use the memory system to find similar documents
            similar_results = self.memory_system.query_memories(
                content[:500],  # Use first part of content for similarity search
                k=5,
                use_smart_routing=False  # Direct search for relationship building
            )
            
            if 'content' not in similar_results:
                return
                
            # Process similar documents to establish relationships
            for result_block in similar_results['content']:
                try:
                    # Extract metadata from result text (this is a simplified approach)
                    result_text = result_block.get('text', '')
                    if 'Metadata:' in result_text:
                        # This is a basic parsing - in production you'd want more robust metadata extraction
                        pass
                    
                    # For now, establish basic relationships based on content similarity
                    # In a full implementation, you'd extract actual document/chunk IDs from results
                    
                except Exception as e:
                    logging.warning(f"Failed to establish relationship from result: {e}")
                    continue
                    
        except Exception as e:
            logging.warning(f"Failed to establish semantic relationships: {e}")
    
    def handle_deduplication_merge(self, primary_doc_id: str, merged_doc_ids: List[str], 
                                 similarity_scores: List[float]) -> dict:
        """Handle chunk relationships when documents are merged during deduplication.
        
        Args:
            primary_doc_id: ID of the primary (surviving) document
            merged_doc_ids: List of document IDs that were merged
            similarity_scores: Similarity scores for each merged document
            
        Returns:
            Merge relationship summary
        """
        current_time = time.time()
        merge_id = f"merge_{int(current_time * 1000)}"
        
        # Create merge record
        merge_record = {
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
                                'similarity_score': merge_record['similarity_scores'].get(merged_id, 0.0),
                                'merged_into': primary_doc_id
                            })
                    
                    # Mark merged document as consolidated
                    merged_rel['consolidated_into'] = primary_doc_id
                    merged_rel['consolidation_timestamp'] = current_time
                    merge_record['preserved_relationships'].extend(
                        merged_rel.get('related_documents', [])
                    )
            
            # Update primary document relationships
            primary_rel['related_documents'] = list(all_related_docs)
            primary_rel['consolidated_chunk_count'] = consolidated_chunk_count
            primary_rel['merge_benefit_score'] = sum(similarity_scores) / len(similarity_scores)
        
        # Store merge record
        self.merge_history[merge_id] = merge_record
        
        logging.info(f"Handled deduplication merge: {len(merged_doc_ids)} documents merged into {primary_doc_id}")
        
        return {
            'merge_id': merge_id,
            'documents_merged': len(merged_doc_ids),
            'relationships_preserved': len(merge_record['preserved_relationships']),
            'average_similarity': sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
        }
    
    def retrieve_related_chunks(self, found_chunk_id: str, k_related: int = None) -> List[Dict[str, Any]]:
        """Get related chunks when one chunk is found relevant.
        
        Args:
            found_chunk_id: ID of the chunk that was found relevant
            k_related: Number of related chunks to retrieve (default from config)
            
        Returns:
            List of related chunk information with context
        """
        if k_related is None:
            k_related = self.config['max_related_chunks']
        
        if found_chunk_id not in self.chunk_relationships:
            # Try to find relationships by looking in the memory system directly
            related_chunks = []
            try:
                # Search across all memory collections
                for collection_name in ['short_term_memory', 'long_term_memory']:
                    collection = getattr(self.memory_system, collection_name, None)
                    if collection and hasattr(collection, 'get'):
                        try:
                            result = collection.get()
                            if result and 'metadatas' in result and 'ids' in result:
                                for i, (chunk_id, metadata) in enumerate(zip(result['ids'], result['metadatas'])):
                                    if chunk_id == found_chunk_id and metadata:
                                        # Found the chunk, now look for its relationships
                                        # Note: Relationships are now stored in internal relationship manager
                                        relationships = []  # Will be retrieved from chunk_relationships dict below
                                        for rel in relationships:
                                            target_chunk_id = rel.get('target_chunk_id')
                                            # Find the target chunk content
                                            for j, (target_id, target_meta) in enumerate(zip(result['ids'], result['metadatas'])):
                                                if target_id == target_chunk_id:
                                                    related_chunks.append({
                                                        'chunk_id': target_chunk_id,
                                                        'document_id': target_meta.get('document_id', 'unknown'),
                                                        'chunk_index': target_meta.get('chunk_index', 0),
                                                        'relationship_type': rel.get('type', 'unknown'),
                                                        'content_preview': result['documents'][j] if j < len(result['documents']) else 'No content',
                                                        'context_relevance': rel.get('context_relevance', rel.get('score', 0.0))
                                                    })
                                        return related_chunks[:k_related]
                        except Exception as e:
                            logging.debug(f"Error accessing {collection_name}: {e}")
                            continue
                
                # If we can't find it in memory system, try to parse the chunk ID format
                parts = found_chunk_id.split('_chunk_')
                if len(parts) == 2:
                    document_id = parts[0]
                    chunk_index = int(parts[1])
                    
                    # Create minimal relationship entry
                    self.chunk_relationships[found_chunk_id] = {
                        'chunk_id': found_chunk_id,
                        'document_id': document_id,
                        'chunk_index': chunk_index,
                        'content_preview': f"Chunk {chunk_index}",
                        'related_chunks': [],
                        'deduplication_sources': [],
                        'access_history': [],
                        'relationship_strength': {},
                        'complex_relationships': {}
                    }
                    logging.debug(f"Created minimal relationship entry for chunk {found_chunk_id}")
                else:
                    logging.warning(f"Chunk {found_chunk_id} not found in relationships and cannot parse ID format")
                    return []
            except (ValueError, IndexError):
                logging.warning(f"Chunk {found_chunk_id} not found in relationships and cannot parse chunk index")
                return []
        
        chunk_rel = self.chunk_relationships[found_chunk_id]
        document_id = chunk_rel['document_id']
        
        related_chunks = []
        
        try:
            # Get adjacent chunks from same document
            if document_id in self.document_relationships:
                doc_rel = self.document_relationships[document_id]
                chunk_index = chunk_rel['chunk_index']
                
                # Calculate range of related chunks
                start_idx = max(0, chunk_index - k_related // 2)
                end_idx = min(doc_rel['chunk_count'], chunk_index + k_related // 2 + 1)
                
                for i in range(start_idx, end_idx):
                    if i != chunk_index:  # Don't include the original chunk
                        related_chunk_id = f"{document_id}_chunk_{i}"
                        if related_chunk_id in self.chunk_relationships:
                            related_rel = self.chunk_relationships[related_chunk_id]
                            related_chunks.append({
                                'chunk_id': related_chunk_id,
                                'document_id': document_id,
                                'chunk_index': i,
                                'relationship_type': 'adjacent',
                                'distance_from_source': abs(i - chunk_index),
                                'content_preview': related_rel['content_preview'],
                                'deduplication_sources': related_rel['deduplication_sources'],
                                'context_relevance': 1.0 - (abs(i - chunk_index) / k_related)
                            })
            
            # Get semantic relationships from related_chunks field
            semantic_related = chunk_rel.get('related_chunks', [])
            for rel in semantic_related:
                target_chunk_id = rel.get('target_chunk_id')
                if target_chunk_id and target_chunk_id in self.chunk_relationships:
                    target_rel = self.chunk_relationships[target_chunk_id]
                    related_chunks.append({
                        'chunk_id': target_chunk_id,
                        'document_id': target_rel.get('document_id', 'unknown'),
                        'chunk_index': target_rel.get('chunk_index', 0),
                        'relationship_type': rel.get('type', 'semantic'),
                        'content_preview': target_rel.get('content_preview', 'No preview'),
                        'context_relevance': rel.get('context_relevance', rel.get('score', 0.0))
                    })
                elif target_chunk_id:
                    # Try to find the target in memory collections if not in internal tracking
                    target_content = self._find_chunk_content_in_collections(target_chunk_id)
                    if target_content:
                        related_chunks.append({
                            'chunk_id': target_chunk_id,
                            'document_id': 'unknown',
                            'chunk_index': 0,
                            'relationship_type': rel.get('type', 'semantic'),
                            'content_preview': target_content[:100] + '...' if len(target_content) > 100 else target_content,
                            'context_relevance': rel.get('context_relevance', rel.get('score', 0.0))
                        })
            
            # Get chunks from merged documents (deduplication-aware)
            merge_related_chunks = self._get_merge_related_chunks(found_chunk_id, document_id, k_related)
            related_chunks.extend(merge_related_chunks)
            
            # Sort by relevance and limit results
            related_chunks.sort(key=lambda x: x.get('context_relevance', 0), reverse=True)
            return related_chunks[:k_related]
            
        except Exception as e:
            logging.error(f"Failed to retrieve related chunks for {found_chunk_id}: {e}")
            return []
    
    def _find_chunk_content_in_collections(self, chunk_id: str) -> str:
        """Find chunk content in memory collections."""
        try:
            for collection_name in ['short_term_memory', 'long_term_memory']:
                collection = getattr(self.memory_system, collection_name, None)
                if collection and hasattr(collection, 'get'):
                    result = collection.get()
                    if result and 'ids' in result and 'documents' in result:
                        for i, (id_val, doc_content) in enumerate(zip(result['ids'], result['documents'])):
                            if id_val == chunk_id:
                                return doc_content
        except Exception as e:
            logging.debug(f"Error finding chunk content for {chunk_id}: {e}")
        return None

    def _get_merge_related_chunks(self, source_chunk_id: str, document_id: str, 
                                 k_related: int) -> List[Dict[str, Any]]:
        """Get chunks from documents that were merged during deduplication."""
        merge_related = []
        
        try:
            # Check if this document has deduplication history
            if document_id in self.document_relationships:
                doc_rel = self.document_relationships[document_id]
                
                for merge_info in doc_rel.get('deduplication_history', []):
                    for source_doc_id in merge_info.get('source_documents', []):
                        if source_doc_id in self.document_relationships:
                            source_doc_rel = self.document_relationships[source_doc_id]
                            
                            # Add chunks from merged source documents
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
                                        'deduplication_sources': chunk_rel['deduplication_sources'],
                                        'context_relevance': 0.8  # High relevance for merged content
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
    
    def get_document_context(self, document_id: str) -> Dict[str, Any]:
        """Get comprehensive context for a document including relationships and history."""
        if document_id not in self.document_relationships:
            return {'error': 'Document not found in relationships'}
        
        doc_rel = self.document_relationships[document_id]
        current_time = time.time()
        
        context = {
            'document_id': document_id,
            'creation_time': doc_rel['creation_time'],
            'age_days': (current_time - doc_rel['creation_time']) / 86400,
            'chunk_count': doc_rel['chunk_count'],
            'collection': doc_rel['collection'],
            'language': doc_rel['language'],
            'deduplication_history': doc_rel.get('deduplication_history', []),
            'related_documents': doc_rel.get('related_documents', []),
            'consolidation_info': {}
        }
        
        # Add consolidation information if applicable
        if 'consolidated_chunk_count' in doc_rel:
            context['consolidation_info'] = {
                'is_consolidated': True,
                'original_chunk_count': doc_rel['chunk_count'],
                'total_consolidated_chunks': doc_rel['consolidated_chunk_count'],
                'consolidation_ratio': doc_rel['consolidated_chunk_count'] / doc_rel['chunk_count'],
                'merge_benefit_score': doc_rel.get('merge_benefit_score', 0.0)
            }
        
        # Add merge history details
        merge_count = len(doc_rel.get('deduplication_history', []))
        if merge_count > 0:
            context['merge_statistics'] = {
                'total_merges': merge_count,
                'documents_absorbed': sum(
                    len(merge.get('source_documents', [])) 
                    for merge in doc_rel['deduplication_history']
                ),
                'latest_merge': max(
                    merge['merge_timestamp'] 
                    for merge in doc_rel['deduplication_history']
                ) if doc_rel['deduplication_history'] else None
            }
        
        return context
    
    def get_relationship_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about chunk relationships and deduplication."""
        current_time = time.time()
        
        # Count relationships across all memory collections
        total_chunks_analyzed = 0
        total_relationships_found = 0
        relationship_types = {}
        
        # Try to get data from memory system collections
        try:
            for collection in ['short_term_memory', 'long_term_memory']:
                memory_collection = getattr(self.memory_system, collection, None)
                if memory_collection and hasattr(memory_collection, 'get'):
                    try:
                        result = memory_collection.get()
                        if result and 'metadatas' in result:
                            for metadata in result['metadatas']:
                                if metadata and isinstance(metadata, dict):
                                    total_chunks_analyzed += 1
                                    # Note: Relationships are now stored in internal relationship manager
                                    # Get from chunk_relationships dict instead of metadata
                                    chunk_id = metadata.get('chunk_id')
                                    if chunk_id and chunk_id in self.chunk_relationships:
                                        chunk_rel = self.chunk_relationships[chunk_id]
                                        relationships = chunk_rel.get('related_chunks', [])
                                        if relationships:
                                            total_relationships_found += len(relationships)
                                            for rel in relationships:
                                                rel_type = rel.get('type', 'unknown')
                                                relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
                    except Exception as e:
                        # If collection access fails, use internal tracking
                        pass
        except Exception as e:
            # Fallback to internal tracking
            total_chunks_analyzed = len(self.chunk_relationships)
        
        stats = {
            'total_documents': len(self.document_relationships),
            'total_chunks': len(self.chunk_relationships),
            'total_chunks_analyzed': total_chunks_analyzed,
            'total_relationships_found': total_relationships_found,
            'relationship_types_distribution': relationship_types,
            'total_merges': len(self.merge_history),
            'documents_with_merges': 0,
            'average_chunks_per_document': 0,
            'relationship_health': {},
            'deduplication_impact': {},
            'recent_activity': {}
        }
        
        # Calculate basic statistics
        if self.document_relationships:
            chunk_counts = [doc.get('chunk_count', 0) for doc in self.document_relationships.values()]
            stats['average_chunks_per_document'] = sum(chunk_counts) / len(chunk_counts)
            
            # Count documents with merge history
            stats['documents_with_merges'] = sum(
                1 for doc in self.document_relationships.values()
                if doc.get('deduplication_history')
            )
        
        # Deduplication impact analysis
        total_original_chunks = sum(
            doc.get('chunk_count', 0) 
            for doc in self.document_relationships.values()
        )
        total_consolidated_chunks = sum(
            doc.get('consolidated_chunk_count', doc.get('chunk_count', 0))
            for doc in self.document_relationships.values()
        )
        
        if total_original_chunks > 0:
            stats['deduplication_impact'] = {
                'original_chunks': total_original_chunks,
                'consolidated_chunks': total_consolidated_chunks,
                'consolidation_ratio': total_consolidated_chunks / total_original_chunks,
                'space_savings_percentage': ((total_consolidated_chunks - total_original_chunks) / total_original_chunks) * 100
            }
        
        # Recent activity (last 24 hours)
        day_ago = current_time - 86400
        recent_documents = sum(
            1 for doc in self.document_relationships.values()
            if doc.get('creation_time', 0) > day_ago
        )
        recent_merges = sum(
            1 for merge in self.merge_history.values()
            if merge.get('timestamp', 0) > day_ago
        )
        
        stats['recent_activity'] = {
            'documents_created_24h': recent_documents,
            'merges_performed_24h': recent_merges,
            'activity_score': (recent_documents + recent_merges * 2) / 10.0  # Normalized activity score
        }
        
        return stats

    def _update_relationships_semantic(self, doc: Document, candidates: List[Document], collection_name: str):
        """Update semantic relationships between documents."""
        doc_metadata = doc.metadata.copy()
        # Note: Relationships are now stored in internal relationship manager instead of ChromaDB metadata
        chunk_id = doc_metadata.get('chunk_id')
        if not chunk_id:
            return  # Cannot establish relationships without chunk_id
        
        for candidate in candidates:
            # Calculate similarity using the deduplicator's similarity calculator
            similarity = self.memory_system.deduplicator.similarity_calculator.calculate_similarity(
                doc.page_content, candidate.page_content
            )
            
            # Only add relationship if similarity exceeds threshold
            if similarity >= self.config['semantic_similarity_threshold']:
                relationship = {
                    'target_chunk_id': candidate.metadata.get('chunk_id'),
                    'type': 'semantic_similarity',
                    'score': similarity,
                    'context_relevance': min(1.0, similarity + 0.1)
                }
                # Store relationship in internal relationship manager
                if chunk_id in self.chunk_relationships:
                    if 'related_chunks' not in self.chunk_relationships[chunk_id]:
                        self.chunk_relationships[chunk_id]['related_chunks'] = []
                    self.chunk_relationships[chunk_id]['related_chunks'].append(relationship)
        
        # Update the document metadata through the memory system
        self.memory_system.update_document_metadata(doc.metadata.get('chunk_id'), doc_metadata)

    def _update_relationships_co_occurrence(self, docs: List[Document], collection_name: str):
        """Update co-occurrence relationships between documents."""
        # Extract common terms from documents
        doc_terms = []
        for doc in docs:
            terms = set(doc.page_content.lower().split())
            doc_terms.append(terms)
        
        # Find co-occurrence relationships
        for i, doc1 in enumerate(docs):
            doc1_terms = doc_terms[i]
            relationships = []
            
            for j, doc2 in enumerate(docs):
                if i != j:  # Don't compare with self
                    doc2_terms = doc_terms[j]
                    common_terms = doc1_terms.intersection(doc2_terms)
                    
                    # If there are enough common terms, create a co-occurrence relationship
                    if len(common_terms) >= 2:  # At least 2 common terms
                        co_occurrence_score = len(common_terms) / len(doc1_terms.union(doc2_terms))
                        relationship = {
                            'target_chunk_id': doc2.metadata.get('chunk_id'),
                            'type': 'co_occurrence',
                            'score': co_occurrence_score,
                            'common_terms': list(common_terms)
                        }
                        relationships.append(relationship)
            
            # Update internal relationship manager if relationships were found
            if relationships:
                chunk_id = doc1.metadata.get('chunk_id')
                if chunk_id and chunk_id in self.chunk_relationships:
                    if 'related_chunks' not in self.chunk_relationships[chunk_id]:
                        self.chunk_relationships[chunk_id]['related_chunks'] = []
                    self.chunk_relationships[chunk_id]['related_chunks'].extend(relationships)