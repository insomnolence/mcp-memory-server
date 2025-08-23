import time
import json
import random
import logging
import asyncio
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_chroma import Chroma
from langchain_core.documents import Document

from .scorer import MemoryImportanceScorer
from .query_monitor import QueryPerformanceMonitor
from .chunk_relationships import ChunkRelationshipManager
from ..deduplication import MemoryDeduplicator
from ..analytics import MemoryIntelligenceSystem


class HierarchicalMemorySystem:
    """Four-tier hierarchical memory system with intelligent importance-based routing."""
    
    def __init__(self, db_config: dict, embeddings_config: dict, memory_config: dict, scoring_config: dict, deduplication_config: dict = None):
        """Initialize the hierarchical memory system.
        
        Args:
            db_config: Database configuration
            embeddings_config: Embedding model configuration
            memory_config: Memory management configuration
            scoring_config: Scoring algorithm configuration
            deduplication_config: Deduplication configuration
        """
        self.persist_directory = db_config.get('persist_directory', './chroma_db_advanced')
        self.collection_names = db_config.get('collections', {})
        
        # Embedding Model
        self.embedding_model_name = embeddings_config.get('model_name', 'sentence-transformers/all-MiniLM-L6-v2')
        self.embedding_function = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        self.chunk_size = embeddings_config.get('chunk_size', 1000)
        self.chunk_overlap = embeddings_config.get('chunk_overlap', 100)
        
        # Lifecycle manager (set after initialization)
        self.lifecycle_manager = None
        
        # Initialize memory collections with error handling
        try:
            self.short_term_memory = Chroma(
                collection_name=self.collection_names.get('short_term', 'short_term_memory'),
                embedding_function=self.embedding_function,
                persist_directory=self.persist_directory,
            )
            
            self.long_term_memory = Chroma(
                collection_name=self.collection_names.get('long_term', 'long_term_memory'), 
                embedding_function=self.embedding_function,
                persist_directory=self.persist_directory,
            )
            
            logging.info(f"Successfully initialized all memory collections in {self.persist_directory}")
            
        except Exception as init_error:
            logging.error(f"Failed to initialize memory collections: {init_error}")
            raise RuntimeError(f"Memory system initialization failed: {init_error}") from init_error
        
        self.importance_scorer = MemoryImportanceScorer(scoring_config)
        
        # Initialize chunk relationship manager first (needed by deduplicator)
        self.chunk_manager = ChunkRelationshipManager(self, memory_config.get('chunk_relationships', {}))
        
        # Initialize deduplication system with chunk manager
        if deduplication_config is None:
            deduplication_config = {'enabled': False}
        self.deduplicator = MemoryDeduplicator(deduplication_config, self.chunk_manager)
        
        # Initialize query performance monitor
        self.query_monitor = QueryPerformanceMonitor(memory_config.get('query_monitoring', {}))
        
        # Initialize analytics and intelligence system
        self.intelligence_system = MemoryIntelligenceSystem(self, memory_config.get('analytics', {}))
        
        # Maintenance settings from config
        self.short_term_max_size = memory_config.get('short_term_max_size', 100)
        self.short_term_threshold = memory_config.get('short_term_threshold', 0.7)
        self.long_term_threshold = memory_config.get('long_term_threshold', 0.95)
    
    async def add_memory(self, content: str, metadata: dict = None, context: dict = None, memory_type: str = "auto") -> dict:
        """Add memory to appropriate collection based on importance.
        
        Args:
            content: Text content to store
            metadata: Optional metadata dictionary
            context: Optional context for importance scoring
            memory_type: Target collection type ("auto", "short_term", "long_term")
            
        Returns:
            Dictionary with operation results and statistics
        """
        if metadata is None:
            metadata = {}
            
        # Calculate importance score
        importance = self.importance_scorer.calculate_importance(content, metadata, context)
        
        # Check for duplicates during ingestion if deduplication is enabled
        if self.deduplicator.enabled:
            # First determine target collection to check against
            temp_collection = (self.long_term_memory if importance > self.short_term_threshold 
                             else self.short_term_memory)
            
            action, existing_doc, similarity = self.deduplicator.check_ingestion_duplicates(
                content, metadata, temp_collection
            )
            
            if action == 'boost_existing' and existing_doc:
                # Boost existing document instead of adding duplicate
                updated_metadata = self.deduplicator.boost_existing_document(existing_doc, metadata)
                logging.info(f"Boosted existing document instead of adding duplicate (similarity: {similarity:.3f})")
                return {
                    "success": True,
                    "message": f"Boosted existing similar document instead of adding duplicate",
                    "action": "boosted_existing",
                    "similarity_score": similarity,
                    "importance_score": importance,
                    "collection": "existing",
                    "chunks_added": 0
                }
            elif action == 'merge_content' and existing_doc:
                # Could implement content merging here if desired
                logging.info(f"Similar content detected (similarity: {similarity:.3f}), adding as new document")
        
        # Determine target collection
        if memory_type == "auto":
            if importance >= self.long_term_threshold:
                target_collection = self.long_term_memory
                collection_name = "long_term"
            elif importance >= self.short_term_threshold:
                target_collection = self.short_term_memory
                collection_name = "short_term"
            else:
                # Default to short_term if below short_term_threshold
                target_collection = self.short_term_memory
                collection_name = "short_term"
        elif memory_type == "long_term":
            target_collection = self.long_term_memory
            collection_name = "long_term"
        else:
            target_collection = self.short_term_memory
            collection_name = "short_term"
        
        # Prepare enhanced metadata
        enhanced_metadata = metadata.copy()
        enhanced_metadata.update({
            'timestamp': time.time(),
            'importance_score': importance,
            'access_count': 0,
            'last_accessed': time.time(),
            'collection_type': collection_name,
            'context': json.dumps(context) if context else '{}'
        })
        
        # Apply TTL and lifecycle metadata if lifecycle manager is available
        if self.lifecycle_manager:
            enhanced_metadata = self.lifecycle_manager.process_document_lifecycle(content, enhanced_metadata, importance)
        
        # Generate unique ID
        memory_id = f"{collection_name}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        # Process and chunk content
        language = metadata.get('language', 'text')
        chunks = self._chunk_content(content, language)
        
        # Filter complex metadata before creating documents
        filtered_metadata = self._filter_complex_metadata(enhanced_metadata)
        
        # Create documents with enhanced relationship tracking
        documents = self.chunk_manager.create_document_with_relationships(
            content=content,
            metadata=filtered_metadata,
            chunks=chunks,
            memory_id=memory_id,
            collection_name=collection_name
        )
        
        # Add to collection with error handling
        try:
            await asyncio.to_thread(target_collection.add_documents, documents)
            
            # Trigger maintenance if needed
            if collection_name == "short_term":
                try:
                    self._maintain_short_term_memory()
                except Exception as maintenance_error:
                    logging.warning(f"Memory maintenance failed after adding documents: {maintenance_error}")
            
            return {
                "success": True,
                "message": f"Added {len(documents)} chunks to {collection_name} memory",
                "memory_id": memory_id,
                "importance_score": importance,
                "collection": collection_name,
                "chunks_added": len(documents),
                "action": "added"
            }
            
        except Exception as db_error:
            logging.error(f"Database error adding documents to {collection_name}: {db_error}")
            return {
                "success": False,
                "message": f"Failed to add documents to {collection_name} memory: {str(db_error)}",
                "memory_id": memory_id,
                "importance_score": importance,
                "collection": collection_name,
                "chunks_added": 0,
                "error": str(db_error)
            }
    
    def query_memories(self, query: str, collections: List[str] = None, k: int = 5, use_smart_routing: bool = True) -> dict:
        """Query across memory collections with deduplication-aware intelligent routing.
        
        Args:
            query: Search query string
            collections: List of collection names to search (default: smart routing)
            k: Maximum number of results to return
            use_smart_routing: Whether to use deduplication-aware smart routing
            
        Returns:
            Dictionary containing formatted search results
        """
        # Start performance tracking
        start_time = time.time()
        current_time = start_time
        
        # Use smart routing if enabled and collections not explicitly specified
        if use_smart_routing and collections is None:
            collections, collection_limits, effective_k = self._smart_query_routing(query, k)
        else:
            if collections is None:
                collections = ["short_term", "long_term"]
            collection_limits = [k // len(collections)] * len(collections)
            effective_k = k
        
        all_results = []
        
        # Query each collection with smart limits
        for i, collection_name in enumerate(collections):
            collection = getattr(self, f"{collection_name}_memory", None)
            if collection is None:
                continue
                
            # Use collection-specific limits from smart routing
            collection_k = collection_limits[i] if i < len(collection_limits) else effective_k
            search_k = max(collection_k * 2, 10)  # Get extra candidates for better ranking
                
            try:
                initial_docs = collection.similarity_search_with_score(query, k=search_k)
                
                for doc, distance in initial_docs:
                    memory_data = {
                        'document': doc.page_content,
                        'metadata': doc.metadata,
                        'distance': distance,
                        'collection': collection_name
                    }
                    
                    # Enhanced retrieval score with deduplication awareness
                    retrieval_score = self._calculate_enhanced_retrieval_score(
                        memory_data, query, current_time
                    )
                    memory_data['retrieval_score'] = retrieval_score
                    
                    all_results.append(memory_data)
                    
            except Exception as e:
                logging.warning(f"Error querying {collection_name} collection: {e}")
                continue
        
        # Sort by retrieval score and take top k
        all_results.sort(key=lambda x: x['retrieval_score'], reverse=True)
        top_results = all_results[:effective_k]
        
        # Update access statistics for retrieved memories
        self._update_access_stats(top_results)
        
        # Format for MCP response with enhanced metadata and related chunks
        content_blocks = []
        related_chunks_included = 0
        
        for result in top_results:
            # Add deduplication information if available
            dedup_info = ""
            if result['metadata'].get('duplicate_sources'):
                dedup_info = f" | Merged from {len(result['metadata']['duplicate_sources'])} sources"
            
            # Get related chunks for better context
            related_chunks = []
            chunk_id = result['metadata'].get('chunk_id')
            if chunk_id and hasattr(self, 'chunk_manager'):
                try:
                    related_chunks = self.chunk_manager.retrieve_related_chunks(chunk_id, k_related=2)
                    if related_chunks:
                        related_chunks_included += len(related_chunks)
                except Exception as e:
                    logging.warning(f"Failed to retrieve related chunks for {chunk_id}: {e}")
            
            # Format main result
            result_text = f"**Score: {result['retrieval_score']:.3f} | Collection: {result['collection']}{dedup_info}**\n\n{result['document']}\n\n"
            
            # Add related chunks context if available
            if related_chunks:
                result_text += "**Related Context:**\n"
                for i, related in enumerate(related_chunks[:2]):  # Limit to 2 most relevant
                    relation_type = related.get('relationship_type', 'related')
                    relevance = related.get('context_relevance', 0.0)
                    
                    result_text += f"*{relation_type.replace('_', ' ').title()} (relevance: {relevance:.2f}):*\n"
                    result_text += f"{related.get('content_preview', 'No preview available')}\n\n"
            
            result_text += f"**Metadata:** {result['metadata']}"
            
            content_blocks.append({
                "type": "text", 
                "text": result_text,
                "metadata": result['metadata']  # Include metadata as separate field for MCP compatibility
            })
        
        # Calculate processing time and create results
        processing_time = time.time() - start_time
        
        results = {
            "content": content_blocks,
            "total_results": len(all_results),
            "collections_searched": collections,
            "smart_routing_used": use_smart_routing and collections != ["short_term", "long_term"],
            "query_optimization_applied": use_smart_routing,
            "processing_time_ms": processing_time * 1000,
            "related_chunks_included": related_chunks_included,
            "context_enhancement_enabled": hasattr(self, 'chunk_manager')
        }
        
        # Track query performance
        try:
            query_metadata = {
                'effective_k': effective_k,
                'original_k': k,
                'collection_limits': collection_limits
            }
            self.query_monitor.track_query(query, results, processing_time, query_metadata)
        except Exception as e:
            logging.warning(f"Failed to track query performance: {e}")
        
        return results
    
    def _smart_query_routing(self, query: str, k: int) -> tuple:
        """Deduplication-aware smart query routing."""
        # Estimate query importance
        query_importance = self._estimate_query_importance(query)
        
        # Get deduplication statistics for routing decisions
        dedup_stats = {}
        if hasattr(self, 'deduplicator') and self.deduplicator.enabled:
            dedup_stats = self.deduplicator.get_deduplication_stats()
        
        # Adjust k based on deduplication effectiveness
        effective_k = self._adjust_k_for_deduplication(k, dedup_stats)
        
        # Route based on importance and deduplication quality
        if query_importance > 0.8:
            # High-importance: long-term has higher quality post-deduplication
            search_order = ['long_term', 'short_term']
            collection_limits = [effective_k // 2 + 1, effective_k // 2]
        elif query_importance > 0.5:
            # Medium-importance: balanced approach
            search_order = ['short_term', 'long_term'] 
            collection_limits = [effective_k // 2, effective_k // 2]
        else:
            # Low-importance: short-term first, but with deduplication benefits
            search_order = ['short_term', 'long_term']
            collection_limits = [effective_k // 2 + 1, effective_k // 2]
        
        return search_order, collection_limits, effective_k
    
    def _estimate_query_importance(self, query: str) -> float:
        """Estimate query importance based on content patterns."""
        # Basic importance estimation
        importance = 0.5  # Default medium importance
        
        # Boost for technical/specific terms
        technical_patterns = ['error', 'bug', 'implementation', 'algorithm', 'function', 'class', 'method']
        if any(pattern in query.lower() for pattern in technical_patterns):
            importance += 0.2
        
        # Boost for question words indicating detailed requests
        question_patterns = ['how', 'why', 'what', 'where', 'when', 'which']
        if any(pattern in query.lower() for pattern in question_patterns):
            importance += 0.1
        
        # Boost for longer, more detailed queries
        if len(query.split()) > 10:
            importance += 0.1
        elif len(query.split()) > 5:
            importance += 0.05
        
        # Check if query matches common deduplication patterns
        if hasattr(self, 'deduplicator') and self.deduplicator.enabled:
            if self._matches_common_dedup_patterns(query):
                importance += 0.1  # Boost for common patterns that benefit from deduplication
        
        return min(importance, 1.0)
    
    def _matches_common_dedup_patterns(self, query: str) -> bool:
        """Check if query matches patterns commonly found in deduplicated content."""
        try:
            # This could be enhanced to check against actual deduplication patterns
            # For now, use simple heuristics
            common_patterns = ['duplicate', 'similar', 'same', 'identical', 'repeated']
            return any(pattern in query.lower() for pattern in common_patterns)
        except:
            return False
    
    def _adjust_k_for_deduplication(self, requested_k: int, dedup_stats: dict) -> int:
        """Adjust search parameters based on deduplication effectiveness."""
        if not dedup_stats:
            return requested_k
        
        # Get deduplication effectiveness
        effectiveness = dedup_stats.get('deduplication_efficiency', 0) / 100.0
        
        if effectiveness > 0.3:
            # High deduplication means higher quality results, can use smaller k
            return max(requested_k - 2, 3)
        elif effectiveness > 0.1:
            # Moderate deduplication
            return max(requested_k - 1, 3) 
        else:
            # Low deduplication, maintain original k
            return requested_k
    
    def _calculate_enhanced_retrieval_score(self, memory_data: dict, query: str, current_time: float) -> float:
        """Calculate retrieval score with deduplication awareness."""
        # Base retrieval score
        base_score = self.importance_scorer.calculate_retrieval_score(
            memory_data, query, current_time
        )
        
        # Deduplication boost for merged documents
        dedup_boost = 0.0
        metadata = memory_data.get('metadata', {})
        
        if metadata.get('duplicate_sources'):
            # Documents that were merged from duplicates likely have higher quality
            source_count = len(metadata['duplicate_sources'])
            dedup_boost = min(source_count * 0.02, 0.1)  # Up to 10% boost
        
        # Boost for documents with high similarity scores (indicates they were well-matched)
        similarity_score = metadata.get('similarity_score', 0)
        if similarity_score > 0.9:
            dedup_boost += 0.05  # 5% boost for high-confidence matches
        
        return min(base_score + dedup_boost, 1.0)
    
    def _chunk_content(self, content: str, language: str = "text") -> List[str]:
        """Chunk content based on language type.
        
        Args:
            content: Text content to chunk
            language: Programming language for intelligent chunking
            
        Returns:
            List of content chunks
        """
        language_map = {
            "python": Language.PYTHON,
            "c++": Language.CPP,
            "markdown": Language.MARKDOWN,
        }
        lang_enum = language_map.get(language.lower(), None)
        
        if lang_enum:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=lang_enum, chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
            )
        
        return splitter.split_text(content)
    
    def _filter_complex_metadata(self, metadata: dict) -> dict:
        """Filter out complex metadata values that ChromaDB cannot handle.
        
        ChromaDB only accepts scalar values: str, int, float, bool, None
        """
        filtered = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                filtered[key] = value
            elif isinstance(value, (list, dict)):
                # Convert complex types to JSON strings
                try:
                    filtered[key] = json.dumps(value)
                except (TypeError, ValueError):
                    # If JSON serialization fails, convert to string representation
                    filtered[key] = str(value)
            else:
                # Convert other types to strings
                filtered[key] = str(value)
        return filtered

    def _maintain_short_term_memory(self):
        """Enhanced memory maintenance with deduplication-aware cleanup."""
        try:
            # Get current document count efficiently
            if hasattr(self.short_term_memory, '_collection'):
                current_count = self.short_term_memory._collection.count()
            else:
                # Fallback to get() method
                result = self.short_term_memory.get()
                current_count = len(result.get('ids', []))
            
            if current_count <= self.short_term_max_size:
                logging.debug(f"Short-term memory within limits: {current_count}/{self.short_term_max_size}")
                return
                
            # Calculate how many documents to remove
            excess_count = current_count - self.short_term_max_size
            logging.info(f"Short-term memory over limit: {current_count}/{self.short_term_max_size}, removing {excess_count} documents")
            
            # Enhanced cleanup with deduplication awareness
            docs_to_remove = self._smart_cleanup_selection(excess_count)
            
            if docs_to_remove:
                self._remove_documents_from_collection(self.short_term_memory, docs_to_remove)
                logging.info(f"Successfully completed smart cleanup of {len(docs_to_remove)} documents")
            
        except Exception as e:
            logging.warning(f"Short-term memory maintenance error: {e}")
    
    def _smart_cleanup_selection(self, target_removal_count: int) -> List[Document]:
        """Enhanced cleanup selection using deduplication-aware strategies."""
        try:
            # Get all documents with metadata efficiently  
            if hasattr(self.short_term_memory, '_collection'):
                chroma_result = self.short_term_memory._collection.get()
                all_docs = []
                for doc_id, content, metadata in zip(
                    chroma_result.get('ids', []),
                    chroma_result.get('documents', []),  
                    chroma_result.get('metadatas', [])
                ):
                    from langchain_core.documents import Document
                    # Ensure metadata exists and add the ChromaDB ID for deletion
                    if metadata is None:
                        metadata = {}
                    metadata['chroma_id'] = doc_id
                    all_docs.append(Document(page_content=content, metadata=metadata))
            else:
                # Fallback to similarity search if direct access unavailable
                all_docs = self.short_term_memory.similarity_search("", k=1000)
            
            if len(all_docs) <= target_removal_count:
                return all_docs[:target_removal_count]
            
            # Phase 1: Remove exact duplicates using deduplication system
            removal_candidates = []
            if self.deduplicator.enabled:
                try:
                    # Find duplicates within the collection
                    duplicates = self.deduplicator.similarity_calculator.find_duplicates_batch(
                        [{'content': doc.page_content, 'metadata': doc.metadata, 'document': doc} 
                         for doc in all_docs],
                        threshold=0.95  # High threshold for exact duplicates
                    )
                    
                    # Add lower-quality duplicates to removal candidates
                    for doc1_data, doc2_data, similarity in duplicates:
                        doc1, doc2 = doc1_data['document'], doc2_data['document']
                        worse_doc = self._choose_worse_document(doc1, doc2)
                        if worse_doc not in removal_candidates:
                            removal_candidates.append(worse_doc)
                            logging.debug(f"Marked duplicate document for removal (similarity: {similarity:.3f})")
                            
                except Exception as dedup_error:
                    logging.warning(f"Deduplication cleanup failed: {dedup_error}")
            
            # Phase 2: If we still need to remove more, use similarity clustering
            remaining_needed = target_removal_count - len(removal_candidates)
            if remaining_needed > 0:
                remaining_docs = [doc for doc in all_docs if doc not in removal_candidates]
                cluster_removals = self._similarity_cluster_cleanup(remaining_docs, remaining_needed)
                removal_candidates.extend(cluster_removals)
            
            # Phase 3: If still need more, fall back to traditional age-based cleanup
            remaining_needed = target_removal_count - len(removal_candidates)
            if remaining_needed > 0:
                remaining_docs = [doc for doc in all_docs if doc not in removal_candidates]
                age_based_removals = self._age_based_cleanup(remaining_docs, remaining_needed)
                removal_candidates.extend(age_based_removals)
            
            return removal_candidates[:target_removal_count]
            
        except Exception as e:
            logging.warning(f"Smart cleanup selection failed: {e}")
            # Fallback to simple age-based cleanup
            return self._age_based_cleanup(all_docs, target_removal_count)
    
    def _choose_worse_document(self, doc1: Document, doc2: Document) -> Document:
        """Choose the worse document from a duplicate pair."""
        def doc_quality_score(doc):
            metadata = doc.metadata
            return (
                metadata.get('importance_score', 0) * 0.5 +
                metadata.get('access_count', 0) * 0.3 + 
                (metadata.get('timestamp', 0) / 86400) * 0.2  # Recency bonus (days)
            )
        
        return doc1 if doc_quality_score(doc1) < doc_quality_score(doc2) else doc2
    
    def _similarity_cluster_cleanup(self, documents: List[Document], target_count: int) -> List[Document]:
        """Find similar document clusters and remove lower-quality documents."""
        if not self.deduplicator.enabled or len(documents) < 2:
            return []
            
        try:
            # Find similarity clusters at a lower threshold
            similar_pairs = self.deduplicator.similarity_calculator.find_duplicates_batch(
                [{'content': doc.page_content, 'metadata': doc.metadata, 'document': doc} 
                 for doc in documents],
                threshold=0.75  # Lower threshold for similarity clustering
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
                        (time.time() - doc.metadata.get('timestamp', 0)) / -86400 * 0.3  # Newer is better
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
        """Group similar document pairs into clusters."""
        clusters = []
        doc_to_cluster = {}
        
        for doc1_data, doc2_data, similarity in similar_pairs:
            doc1, doc2 = doc1_data['document'], doc2_data['document']
            
            cluster1 = doc_to_cluster.get(id(doc1))
            cluster2 = doc_to_cluster.get(id(doc2))
            
            if cluster1 is None and cluster2 is None:
                # Create new cluster
                new_cluster = [doc1, doc2]
                clusters.append(new_cluster)
                doc_to_cluster[id(doc1)] = new_cluster
                doc_to_cluster[id(doc2)] = new_cluster
            elif cluster1 is None:
                # Add doc1 to doc2's cluster
                cluster2.append(doc1)
                doc_to_cluster[id(doc1)] = cluster2
            elif cluster2 is None:
                # Add doc2 to doc1's cluster
                cluster1.append(doc2)
                doc_to_cluster[id(doc2)] = cluster1
            elif cluster1 != cluster2:
                # Merge clusters
                cluster1.extend(cluster2)
                for doc in cluster2:
                    doc_to_cluster[id(doc)] = cluster1
                clusters.remove(cluster2)
        
        return clusters
    
    def _age_based_cleanup(self, documents: List[Document], target_count: int) -> List[Document]:
        """Traditional age-based cleanup as fallback."""
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
    
    def _remove_documents_from_collection(self, collection, docs_to_remove: List[Document]):
        """Remove documents from the specified collection."""
        if hasattr(collection, '_collection'):
            ids_to_delete = []
            for doc in docs_to_remove:
                # Use the ChromaDB ID we stored in metadata, fallback to hash
                doc_id = doc.metadata.get('chroma_id') or doc.metadata.get('id') or str(hash(doc.page_content))
                ids_to_delete.append(doc_id)
            
            if ids_to_delete:
                try:
                    collection._collection.delete(ids=ids_to_delete)
                    logging.debug(f"Successfully removed {len(ids_to_delete)} documents")
                except Exception as delete_error:
                    logging.warning(f"Could not delete documents: {delete_error}")
                    # Fallback: clear collection if individual deletes fail
                    logging.warning("Attempting collection reset as fallback")
                    collection._collection.delete()
                    logging.warning("Collection cleared due to maintenance issues")
    
    def _update_access_stats(self, results: List[dict]):
        """Update access statistics for retrieved memories.
        
        Args:
            results: List of search result dictionaries
        """
        current_time = time.time()
        
        for result in results:
            try:
                metadata = result['metadata']
                chunk_id = metadata.get('chunk_id')
                collection_name = result['collection']
                
                if chunk_id:
                    collection = getattr(self, f"{collection_name}_memory")
                    
                    # Update metadata (this is a simplified approach)
                    # In production, you'd want a more efficient update mechanism
                    new_access_count = metadata.get('access_count', 0) + 1
                    metadata['access_count'] = new_access_count
                    metadata['last_accessed'] = current_time
                    
            except Exception as e:
                logging.warning(f"Error updating access stats: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all memory collections.
        
        Returns:
            Dictionary with collection statistics
        """
        stats = {"collections": {}}
        
        # Get all memory collection attributes dynamically
        # Only include actual Chroma collection instances, not methods or other attributes
        collection_attrs = []
        for attr in dir(self):
            if attr.endswith('_memory') and not attr.startswith('_'):
                obj = getattr(self, attr)
                # Check if it's a Chroma collection instance
                if hasattr(obj, '_collection') or hasattr(obj, 'get'):
                    collection_attrs.append(attr)
        
        for attr_name in collection_attrs:
            collection = getattr(self, attr_name)
            # Extract collection name from attribute (remove '_memory' suffix)
            collection_name = attr_name.replace('_memory', '')
            try:
                # Use ChromaDB's efficient count() method
                if hasattr(collection, '_collection'):
                    count = collection._collection.count()
                else:
                    # Fallback to get() if count() not available
                    result = collection.get()
                    count = len(result.get('ids', []))
                    
                stats["collections"][collection_name] = {
                    "count": count,
                    "status": "active"
                }
            except Exception as e:
                stats["collections"][collection_name] = {
                    "count": 0,
                    "status": f"error: {str(e)}"
                }
        
        return stats
    
    def get_query_performance_stats(self, time_window: str = 'all') -> Dict[str, Any]:
        """Get query performance statistics.
        
        Args:
            time_window: Time window for statistics ('hour', 'day', 'week', 'all')
            
        Returns:
            Query performance statistics
        """
        try:
            return self.query_monitor.get_performance_summary(time_window)
        except Exception as e:
            logging.warning(f"Failed to get query performance stats: {e}")
            return {'error': str(e), 'message': 'Query monitoring not available'}
    
    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """Get comprehensive system analytics with intelligence insights.
        
        Returns:
            Comprehensive analytics including predictions and recommendations
        """
        try:
            return self.intelligence_system.generate_comprehensive_analytics()
        except Exception as e:
            logging.warning(f"Failed to get comprehensive analytics: {e}")
            return {'error': str(e), 'message': 'Analytics system not available'}
    
    def get_chunk_relationship_stats(self) -> Dict[str, Any]:
        """Get chunk relationship statistics.
        
        Returns:
            Chunk relationship statistics and health metrics
        """
        try:
            if hasattr(self, 'chunk_manager'):
                return self.chunk_manager.get_relationship_statistics()
            else:
                return {'error': 'Chunk relationship manager not available'}
        except Exception as e:
            logging.warning(f"Failed to get chunk relationship stats: {e}")
            return {'error': str(e), 'message': 'Chunk relationship tracking not available'}
    
    def set_lifecycle_manager(self, lifecycle_manager):
        """Set the lifecycle manager for TTL and aging functionality.
        
        Args:
            lifecycle_manager: LifecycleManager instance
        """
        self.lifecycle_manager = lifecycle_manager
        logging.info("Lifecycle manager integrated with hierarchical memory system")