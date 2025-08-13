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


class HierarchicalMemorySystem:
    """Four-tier hierarchical memory system with intelligent importance-based routing."""
    
    def __init__(self, db_config: dict, embeddings_config: dict, memory_config: dict, scoring_config: dict):
        """Initialize the hierarchical memory system.
        
        Args:
            db_config: Database configuration
            embeddings_config: Embedding model configuration
            memory_config: Memory management configuration
            scoring_config: Scoring algorithm configuration
        """
        self.persist_directory = db_config.get('persist_directory', './chroma_db_advanced')
        self.collection_names = db_config.get('collections', {})
        
        # Embedding Model
        self.embedding_model_name = embeddings_config.get('model_name', 'sentence-transformers/all-MiniLM-L6-v2')
        self.embedding_function = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        self.chunk_size = embeddings_config.get('chunk_size', 1000)
        self.chunk_overlap = embeddings_config.get('chunk_overlap', 100)
        
        # Initialize memory collections
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
        
        self.consolidated_memory = Chroma(
            collection_name=self.collection_names.get('consolidated', 'consolidated_memory'),
            embedding_function=self.embedding_function,
            persist_directory=self.persist_directory,
        )
        
        # Legacy collection for backward compatibility
        self.legacy_memory = Chroma(
            collection_name=self.collection_names.get('legacy', 'knowledge_base'),
            embedding_function=self.embedding_function,
            persist_directory=self.persist_directory,
        )
        
        self.importance_scorer = MemoryImportanceScorer(scoring_config)
        
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
        
        # Add to collection
        target_collection.add_documents(documents)
        
        # Trigger maintenance if needed
        if collection_name == "short_term":
            self._maintain_short_term_memory()
            
        return {
            "success": True,
            "message": f"Added {len(documents)} chunks to {collection_name} memory",
            "memory_id": memory_id,
            "importance_score": importance,
            "collection": collection_name,
            "chunks_added": len(documents)
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
            collections = ["short_term", "long_term", "consolidated", "legacy"]
        
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
            # Get current count (approximate)
            sample_docs = self.short_term_memory.similarity_search("test", k=1)
            if not sample_docs:
                return
                
            # For now, we'll implement a simple strategy
            # In production, you'd want more sophisticated pruning
            pass
            
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
                
                if chunk_id and collection_name != "legacy":
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
        
        for collection_name in ["short_term", "long_term", "consolidated", "legacy"]:
            collection = getattr(self, f"{collection_name}_memory")
            try:
                # Try to get a sample to check if collection exists and has data
                sample = collection.similarity_search("test", k=1)
                if sample:
                    # Get approximate count by trying larger searches
                    docs_10 = collection.similarity_search("", k=10)
                    docs_100 = collection.similarity_search("", k=100)
                    
                    if len(docs_100) == 100:
                        count = "100+"
                    else:
                        count = len(docs_100)
                else:
                    count = 0
                    
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