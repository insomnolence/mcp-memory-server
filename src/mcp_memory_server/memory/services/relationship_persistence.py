"""
Relationship Persistence Service

Handles serialization, deserialization, and persistence of relationship data
to ChromaDB. This includes:
- JSON serialization/deserialization helpers
- System document management for global metadata (e.g., merge history)
- Chunk relationship persistence
"""

import json
import time
import logging
from typing import Dict, Any, Optional

# Constants for persistence
SYSTEM_DOC_TYPE_MERGE_HISTORY = 'system_merge_history'

# Metadata field names for serialized relationship data
FIELD_RELATED_CHUNKS = 'related_chunks_data'
FIELD_DEDUP_SOURCES = 'dedup_sources_data'
FIELD_RELATIONSHIP_STRENGTH = 'relationship_strength_data'
FIELD_DEDUP_HISTORY = 'dedup_history_data'

# Limits to prevent unbounded growth
MAX_MERGE_HISTORY_SIZE = 1000
MAX_RELATIONSHIPS_PER_CHUNK = 50


class RelationshipPersistenceService:
    """Service for persisting and loading relationship data from ChromaDB.

    This service handles:
    - JSON serialization/deserialization with error handling
    - System document storage and retrieval
    - Chunk relationship persistence
    """

    def __init__(self, memory_system: Any) -> None:
        """Initialize the persistence service.

        Args:
            memory_system: Reference to HierarchicalMemorySystem for ChromaDB access
        """
        self.memory_system = memory_system

    # =========================================================================
    # JSON Serialization Helpers
    # =========================================================================

    def serialize_json(self, data: Any) -> str:
        """Safely serialize data to JSON string for ChromaDB storage.

        Args:
            data: Data to serialize (typically list or dict)

        Returns:
            JSON string, or safe default on error
        """
        try:
            return json.dumps(data)
        except (TypeError, ValueError) as e:
            logging.warning(f"Failed to serialize data to JSON: {e}")
            return '[]' if isinstance(data, list) else '{}'

    def deserialize_json(self, json_str: str, default: Any = None) -> Any:
        """Safely deserialize JSON string with fallback to default.

        Provides backward compatibility for documents without serialized data.

        Args:
            json_str: JSON string to deserialize
            default: Value to return if deserialization fails

        Returns:
            Deserialized data or default value
        """
        if not json_str or json_str == '':
            return default if default is not None else []

        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logging.debug(f"Failed to deserialize JSON (using default): {e}")
            return default if default is not None else []

    # =========================================================================
    # Chunk Relationship Serialization
    # =========================================================================

    def serialize_chunk_relationships(
        self,
        chunk_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Serialize a chunk's relationship data for ChromaDB storage.

        Args:
            chunk_data: The chunk relationship data dict

        Returns:
            Dictionary of serialized fields ready for ChromaDB metadata update
        """
        if not chunk_data:
            return {}

        serialized = {}

        # Serialize related_chunks (limited to prevent unbounded growth)
        related_chunks = chunk_data.get('related_chunks', [])
        if related_chunks:
            limited_relationships = related_chunks[:MAX_RELATIONSHIPS_PER_CHUNK]
            serialized[FIELD_RELATED_CHUNKS] = self.serialize_json(limited_relationships)

        # Serialize deduplication_sources
        dedup_sources = chunk_data.get('deduplication_sources', [])
        if dedup_sources:
            serialized[FIELD_DEDUP_SOURCES] = self.serialize_json(dedup_sources)

        # Serialize relationship_strength
        rel_strength = chunk_data.get('relationship_strength', {})
        if rel_strength:
            serialized[FIELD_RELATIONSHIP_STRENGTH] = self.serialize_json(rel_strength)

        return serialized

    def deserialize_chunk_relationships(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize relationship data from ChromaDB metadata.

        Provides backward compatibility - if fields don't exist, returns empty defaults.

        Args:
            metadata: Raw metadata from ChromaDB

        Returns:
            Dictionary with deserialized relationship data
        """
        return {
            'related_chunks': self.deserialize_json(
                metadata.get(FIELD_RELATED_CHUNKS, ''), default=[]
            ),
            'deduplication_sources': self.deserialize_json(
                metadata.get(FIELD_DEDUP_SOURCES, ''), default=[]
            ),
            'relationship_strength': self.deserialize_json(
                metadata.get(FIELD_RELATIONSHIP_STRENGTH, ''), default={}
            ),
        }

    # =========================================================================
    # System Document Management
    # =========================================================================

    def get_system_document(self, doc_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve a system document by type from ChromaDB.

        Args:
            doc_type: The system document type (e.g., SYSTEM_DOC_TYPE_MERGE_HISTORY)

        Returns:
            The document data if found, None otherwise
        """
        try:
            collection = getattr(self.memory_system, 'short_term_memory', None)
            if not collection or not hasattr(collection, '_collection'):
                return None

            result = collection._collection.get(
                where={'document_type': doc_type}
            )

            if result and result.get('ids') and len(result['ids']) > 0:
                content = result['documents'][0] if result.get('documents') else '{}'
                metadata = result['metadatas'][0] if result.get('metadatas') else {}
                return {
                    'id': result['ids'][0],
                    'content': content,
                    'metadata': metadata,
                    'data': self.deserialize_json(content, default={})
                }
        except Exception as e:
            logging.warning(f"Failed to retrieve system document '{doc_type}': {e}")

        return None

    def save_system_document(self, doc_type: str, data: Dict[str, Any]) -> bool:
        """Save or update a system document in ChromaDB.

        Args:
            doc_type: The system document type
            data: The data to store (will be JSON serialized)

        Returns:
            True if successful, False otherwise
        """
        try:
            collection = getattr(self.memory_system, 'short_term_memory', None)
            if not collection or not hasattr(collection, '_collection'):
                logging.warning("Cannot save system document: collection not available")
                return False

            content = self.serialize_json(data)
            metadata = {
                'document_type': doc_type,
                'is_system_doc': True,
                'updated_at': time.time(),
                'chunk_id': f'__system_{doc_type}__',
                'document_id': f'__system_{doc_type}__',
            }

            existing = self.get_system_document(doc_type)

            if existing:
                collection._collection.update(
                    ids=[existing['id']],
                    documents=[content],
                    metadatas=[metadata]
                )
                logging.debug(f"Updated system document '{doc_type}'")
            else:
                doc_id = f"system_{doc_type}_{int(time.time() * 1000)}"
                collection._collection.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[metadata]
                )
                logging.debug(f"Created system document '{doc_type}'")

            return True

        except Exception as e:
            logging.error(f"Failed to save system document '{doc_type}': {e}")
            return False

    # =========================================================================
    # Chunk Relationship Persistence
    # =========================================================================

    async def persist_chunk_relationships(
        self,
        chunk_id: str,
        chunk_data: Dict[str, Any]
    ) -> bool:
        """Persist a chunk's relationship data to ChromaDB.

        Args:
            chunk_id: The chunk ID to persist
            chunk_data: The chunk relationship data dict

        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = self.serialize_chunk_relationships(chunk_data)
            if not serialized:
                return True  # Nothing to persist

            result = await self.memory_system.update_document_metadata(chunk_id, serialized)
            return bool(result.get('success', False))

        except Exception as e:
            logging.warning(f"Failed to persist relationships for chunk {chunk_id}: {e}")
            return False
