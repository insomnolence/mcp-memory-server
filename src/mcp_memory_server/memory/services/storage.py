"""
Memory Storage Service

Handles document storage operations including:
- Adding documents to collections
- Content chunking
- Metadata filtering for ChromaDB compatibility
- Document removal from collections
"""

import time
import json
import random
import logging
import asyncio
from typing import List, Dict, Any, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_chroma import Chroma

# Import ChromaDB errors for specific exception handling
try:
    from chromadb.errors import ChromaError
except ImportError:
    ChromaError = Exception  # type: ignore[misc, assignment]

# Custom exceptions available for enhanced error handling
# from ..exceptions import StorageError


class MemoryStorageService:
    """Service responsible for document storage operations."""

    def __init__(
        self,
        short_term_memory: Chroma,
        long_term_memory: Chroma,
        chunk_manager: Any,
        importance_scorer: Any,
        deduplicator: Any,
        lifecycle_manager: Any = None,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize storage service.

        Args:
            short_term_memory: Chroma collection for short-term storage
            long_term_memory: Chroma collection for long-term storage
            chunk_manager: ChunkRelationshipManager instance
            importance_scorer: MemoryImportanceScorer instance
            deduplicator: MemoryDeduplicator instance
            lifecycle_manager: Optional LifecycleManager instance
            config: Configuration dictionary
        """
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.chunk_manager = chunk_manager
        self.importance_scorer = importance_scorer
        self.deduplicator = deduplicator
        self.lifecycle_manager = lifecycle_manager

        # Configuration
        config = config or {}
        self.chunk_size = config.get('chunk_size', 1000)
        self.chunk_overlap = config.get('chunk_overlap', 100)
        self.short_term_threshold = config.get('short_term_threshold', 0.7)
        self.long_term_threshold = config.get('long_term_threshold', 0.95)

    def set_lifecycle_manager(self, lifecycle_manager: Any) -> None:
        """Set the lifecycle manager for TTL and aging functionality."""
        self.lifecycle_manager = lifecycle_manager

    async def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        memory_type: str = "auto"
    ) -> Dict[str, Any]:
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

        # Calculate importance score (offload to thread to avoid blocking event loop)
        importance = await asyncio.to_thread(
            self.importance_scorer.calculate_importance, content, metadata, context
        )

        # Check for duplicates during ingestion if deduplication is enabled
        if self.deduplicator.enabled:
            # First determine target collection to check against
            temp_collection = (self.long_term_memory if importance > self.short_term_threshold
                               else self.short_term_memory)

            action, existing_doc, similarity = await self.deduplicator.check_ingestion_duplicates(
                content, metadata, temp_collection
            )

            if action == 'boost_existing' and existing_doc:
                # Boost existing document instead of adding duplicate
                self.deduplicator.boost_existing_document(existing_doc, metadata)
                logging.info(f"Boosted existing document instead of adding duplicate (similarity: {similarity:.3f})")
                return {
                    "success": True,
                    "message": "Boosted existing similar document instead of adding duplicate",
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
            enhanced_metadata = self.lifecycle_manager.process_document_lifecycle(
                content, enhanced_metadata, importance)

        # Generate unique ID
        memory_id = f"{collection_name}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

        # Process and chunk content
        language = metadata.get('language', 'text')
        chunks = self._chunk_content(content, language)

        # Filter complex metadata before creating documents
        filtered_metadata = self._filter_complex_metadata(enhanced_metadata)

        # Create documents with enhanced relationship tracking
        documents = await self.chunk_manager.create_document_with_relationships(
            content=content,
            metadata=filtered_metadata,
            chunks=chunks,
            memory_id=memory_id,
            collection_name=collection_name
        )

        # Add to collection with error handling
        try:
            await asyncio.to_thread(target_collection.add_documents, documents)

            return {
                "success": True,
                "message": f"Added {len(documents)} chunks to {collection_name} memory",
                "memory_id": memory_id,
                "importance_score": importance,
                "collection": collection_name,
                "chunks_added": len(documents),
                "action": "added"
            }

        except ChromaError as db_error:
            logging.error(f"ChromaDB error adding documents to {collection_name}: {db_error}")
            return {
                "success": False,
                "message": f"Database error in {collection_name} memory: {str(db_error)}",
                "memory_id": memory_id,
                "importance_score": importance,
                "collection": collection_name,
                "chunks_added": 0,
                "error": str(db_error),
                "error_type": "storage"
            }
        except (OSError, IOError) as db_error:
            logging.error(f"Filesystem error storing documents: {db_error}")
            return {
                "success": False,
                "message": f"Storage error: {str(db_error)}",
                "memory_id": memory_id,
                "importance_score": importance,
                "collection": collection_name,
                "chunks_added": 0,
                "error": str(db_error),
                "error_type": "filesystem"
            }
        except Exception as db_error:
            logging.error(f"Unexpected error adding documents to {collection_name}: {db_error}")
            return {
                "success": False,
                "message": f"Failed to add documents to {collection_name} memory: {str(db_error)}",
                "memory_id": memory_id,
                "importance_score": importance,
                "collection": collection_name,
                "chunks_added": 0,
                "error": str(db_error),
                "error_type": "unknown"
            }

    def _chunk_content(self, content: str, language: str = "text") -> List[str]:
        """Chunk content based on language type.

        Args:
            content: Content to chunk
            language: Programming language or 'text' for plain text

        Returns:
            List of content chunks
        """
        # Map common language identifiers to RecursiveCharacterTextSplitter languages
        language_map = {
            'python': Language.PYTHON,
            'javascript': Language.JS,
            'typescript': Language.JS,
            'java': Language.JAVA,
            'cpp': Language.CPP,
            'c': Language.CPP,
            'go': Language.GO,
            'rust': Language.RUST,
            'ruby': Language.RUBY,
            'php': Language.PHP,
            'markdown': Language.MARKDOWN,
            'html': Language.HTML,
            'xml': Language.HTML,
            'json': Language.MARKDOWN,
            'yaml': Language.MARKDOWN,
        }

        if language.lower() in language_map:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=language_map[language.lower()],
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )

        return splitter.split_text(content)

    def _filter_complex_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out complex metadata values that ChromaDB cannot handle.

        Args:
            metadata: Original metadata dictionary

        Returns:
            Filtered metadata with only simple types
        """
        filtered = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                filtered[key] = value
            elif isinstance(value, (list, dict)):
                # Convert complex types to JSON strings
                try:
                    filtered[key] = json.dumps(value)
                except (TypeError, ValueError):
                    filtered[key] = str(value)
            elif value is None:
                filtered[key] = ""
            else:
                filtered[key] = str(value)
        return filtered

    def remove_documents_from_collection(self, collection: Chroma, docs_to_remove: List) -> None:
        """Remove documents from the specified collection.

        Args:
            collection: Chroma collection to remove from
            docs_to_remove: List of Document objects to remove
        """
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
                    # Log the error but DO NOT reset the entire collection
                    # That's a dangerous data-loss operation
                    logging.error(
                        f"Failed to delete {len(ids_to_delete)} documents: {delete_error}. "
                        "Documents will be retried on next maintenance cycle."
                    )
