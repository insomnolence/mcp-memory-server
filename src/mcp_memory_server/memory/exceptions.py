"""
Custom exceptions for the memory system.

These exceptions provide more specific error handling than generic Exception
catches, allowing for better debugging and error recovery.
"""


class MemorySystemError(Exception):
    """Base exception for all memory system errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class StorageError(MemorySystemError):
    """Error during storage operations (ChromaDB interactions)."""
    pass


class DocumentNotFoundError(MemorySystemError):
    """Requested document was not found in any collection."""

    def __init__(self, document_id: str, collections_searched: list = None):
        message = f"Document '{document_id}' not found"
        if collections_searched:
            message += f" in collections: {', '.join(collections_searched)}"
        super().__init__(message, {
            'document_id': document_id,
            'collections_searched': collections_searched or []
        })
        self.document_id = document_id


class CollectionError(MemorySystemError):
    """Error related to a specific collection."""

    def __init__(self, collection_name: str, operation: str, cause: str = None):
        message = f"Collection '{collection_name}' error during {operation}"
        if cause:
            message += f": {cause}"
        super().__init__(message, {
            'collection_name': collection_name,
            'operation': operation,
            'cause': cause
        })
        self.collection_name = collection_name
        self.operation = operation


class MaintenanceError(MemorySystemError):
    """Error during memory maintenance operations."""
    pass


class CleanupError(MemorySystemError):
    """Error during cleanup operations."""

    def __init__(self, phase: str, message: str, documents_affected: int = 0):
        full_message = f"Cleanup error in phase '{phase}': {message}"
        super().__init__(full_message, {
            'phase': phase,
            'documents_affected': documents_affected
        })
        self.phase = phase


class DeduplicationError(MemorySystemError):
    """Error during deduplication operations."""
    pass


class ScoringError(MemorySystemError):
    """Error during importance or retrieval scoring."""
    pass


class ChunkRelationshipError(MemorySystemError):
    """Error managing chunk relationships."""

    def __init__(self, chunk_id: str, operation: str, cause: str = None):
        message = f"Chunk relationship error for '{chunk_id}' during {operation}"
        if cause:
            message += f": {cause}"
        super().__init__(message, {
            'chunk_id': chunk_id,
            'operation': operation,
            'cause': cause
        })
        self.chunk_id = chunk_id


class LifecycleError(MemorySystemError):
    """Error during lifecycle management operations."""
    pass


class TTLError(LifecycleError):
    """Error related to TTL calculations or expiry."""
    pass


class StateError(MemorySystemError):
    """Error loading or saving system state."""

    def __init__(self, operation: str, path: str = None, cause: str = None):
        message = f"State {operation} error"
        if path:
            message += f" for '{path}'"
        if cause:
            message += f": {cause}"
        super().__init__(message, {
            'operation': operation,
            'path': path,
            'cause': cause
        })
        self.operation = operation
        self.path = path


class ConfigurationError(MemorySystemError):
    """Error in system configuration."""
    pass
