import time
import json
import random
import logging
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_chroma import Chroma
from langchain_core.documents import Document

from .scorer import MemoryImportanceScorer
from ..deduplication import MemoryDeduplicator


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
        
        # Initialize deduplication system
        if deduplication_config is None:
            deduplication_config = {'enabled': False}
        self.deduplicator = MemoryDeduplicator(deduplication_config)
        
        # Maintenance settings from config
        self.short_term_max_size = memory_config.get('short_term_max_size', 100)
        self.consolidation_threshold = memory_config.get('consolidation_threshold', 50)
        self.importance_threshold = scoring_config.get('importance_threshold', 0.7)
    
    def add_memory(self, content: str, metadata: dict = None, context: dict = None, memory_type: str = "auto") -> dict:
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
            temp_collection = (self.long_term_memory if importance > self.importance_threshold 
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
            if importance > self.importance_threshold:
                target_collection = self.long_term_memory
                collection_name = "long_term"
            else:
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
        
        # Generate unique ID
        memory_id = f"{collection_name}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        # Process and chunk content
        language = metadata.get('language', 'text')
        chunks = self._chunk_content(content, language)
        
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = enhanced_metadata.copy()
            chunk_metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunks),
                'chunk_id': f"{memory_id}_chunk_{i}"
            })
            documents.append(Document(page_content=chunk, metadata=chunk_metadata))
        
        # Add to collection with error handling
        try:
            target_collection.add_documents(documents)
            
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
                "chunks_added": len(documents)
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
    
    def query_memories(self, query: str, collections: List[str] = None, k: int = 5) -> dict:
        """Query across memory collections with intelligent scoring.
        
        Args:
            query: Search query string
            collections: List of collection names to search (default: all)
            k: Maximum number of results to return
            
        Returns:
            Dictionary containing formatted search results
        """
        if collections is None:
            collections = ["short_term", "long_term"]
        
        all_results = []
        current_time = time.time()
        
        # Query each specified collection
        for collection_name in collections:
            collection = getattr(self, f"{collection_name}_memory", None)
            if collection is None:
                continue
                
            try:
                # Get more candidates for reranking
                initial_docs = collection.similarity_search_with_score(query, k=20)
                
                for doc, distance in initial_docs:
                    memory_data = {
                        'document': doc.page_content,
                        'metadata': doc.metadata,
                        'distance': distance,
                        'collection': collection_name
                    }
                    
                    # Calculate retrieval score
                    retrieval_score = self.importance_scorer.calculate_retrieval_score(
                        memory_data, query, current_time
                    )
                    memory_data['retrieval_score'] = retrieval_score
                    
                    all_results.append(memory_data)
                    
            except Exception as e:
                logging.warning(f"Error querying {collection_name} collection: {e}")
                continue
        
        # Sort by retrieval score and take top k
        all_results.sort(key=lambda x: x['retrieval_score'], reverse=True)
        top_results = all_results[:k]
        
        # Update access statistics for retrieved memories
        self._update_access_stats(top_results)
        
        # Format for MCP response
        content_blocks = []
        for result in top_results:
            content_blocks.append({
                "type": "text",
                "text": f"**Score: {result['retrieval_score']:.3f} | Collection: {result['collection']}**\n\n{result['document']}\n\n**Metadata:** {result['metadata']}"
            })
        
        return {
            "content": content_blocks,
            "total_results": len(all_results),
            "collections_searched": collections
        }
    
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
    
    def _maintain_short_term_memory(self):
        """Maintain short-term memory collection size."""
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
            logging.info(f"Short-term memory over limit: {current_count}/{self.short_term_max_size}, removing {excess_count} oldest documents")
            
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
                all_docs = self.short_term_memory.similarity_search("", k=current_count)
            
            # Sort by timestamp (oldest first) - documents should have 'timestamp' in metadata
            docs_with_age = []
            for doc in all_docs:
                timestamp = doc.metadata.get('timestamp', 0)
                access_count = doc.metadata.get('access_count', 0)
                # Prefer removing older and less accessed documents
                priority_score = timestamp + (access_count * 86400)  # Weight access count as days
                docs_with_age.append((priority_score, doc))
            
            # Sort by priority (lower score = older/less accessed = higher removal priority)
            docs_with_age.sort(key=lambda x: x[0])
            
            # Remove oldest documents
            docs_to_remove = [doc for _, doc in docs_with_age[:excess_count]]
            
            # ChromaDB delete requires document IDs
            if hasattr(self.short_term_memory, '_collection'):
                ids_to_delete = []
                for doc in docs_to_remove:
                    # Use the ChromaDB ID we stored in metadata, fallback to hash
                    doc_id = doc.metadata.get('chroma_id') or doc.metadata.get('id') or str(hash(doc.page_content))
                    ids_to_delete.append(doc_id)
                
                if ids_to_delete:
                    try:
                        self.short_term_memory._collection.delete(ids=ids_to_delete)
                        logging.info(f"Successfully removed {len(ids_to_delete)} old documents from short-term memory")
                    except Exception as delete_error:
                        logging.warning(f"Could not delete documents: {delete_error}")
                        # Fallback: clear collection if individual deletes fail
                        logging.warning("Attempting collection reset as fallback")
                        self.short_term_memory._collection.delete()
                        logging.warning("Short-term memory collection cleared due to maintenance issues")
            
        except Exception as e:
            logging.warning(f"Short-term memory maintenance error: {e}")
    
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