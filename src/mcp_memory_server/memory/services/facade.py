"""
Hierarchical Memory System Facade

Provides backward-compatible facade over decomposed services.
This class maintains the exact same public API as the original
HierarchicalMemorySystem while delegating to focused services.
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Import ChromaDB errors for specific exception handling
try:
    from chromadb.errors import ChromaError
except ImportError:
    ChromaError = Exception

from ..scorer import MemoryImportanceScorer
from ..query_monitor import QueryPerformanceMonitor
from ..chunk_relationships import ChunkRelationshipManager
from ..exceptions import StorageError
from ...deduplication import MemoryDeduplicator
from ...analytics import MemoryIntelligenceSystem

from .storage import MemoryStorageService
from .routing import QueryRoutingService
from .query import MemoryQueryService
from .maintenance import MemoryMaintenanceService
from .update import DocumentUpdateService
from .stats import MemoryStatsService


class HierarchicalMemorySystem:
    """Facade providing backward-compatible API over decomposed memory services.

    This class maintains the exact same public interface as the original
    monolithic implementation while delegating to focused service classes.
    """

    def __init__(
        self,
        db_config: Dict[str, Any],
        embeddings_config: Dict[str, Any],
        memory_config: Dict[str, Any],
        scoring_config: Dict[str, Any],
        deduplication_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the hierarchical memory system.

        Args:
            db_config: Database configuration
            embeddings_config: Embedding model configuration
            memory_config: Memory management configuration
            scoring_config: Scoring algorithm configuration
            deduplication_config: Deduplication configuration
        """
        # Store configuration
        self.persist_directory = db_config.get('persist_directory', './chroma_db_advanced')
        self.collection_names = db_config.get('collections', {})

        # Embedding Model
        self.embedding_model_name = embeddings_config.get('model_name', 'sentence-transformers/all-MiniLM-L6-v2')
        self.embedding_function = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        self.chunk_size = embeddings_config.get('chunk_size', 1000)
        self.chunk_overlap = embeddings_config.get('chunk_overlap', 100)

        # Configuration values needed by services
        self.short_term_max_size = memory_config.get('short_term_max_size', 100)
        self.short_term_threshold = memory_config.get('short_term_threshold', 0.7)
        self.long_term_threshold = memory_config.get('long_term_threshold', 0.95)

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

        except ChromaError as init_error:
            logging.error(f"ChromaDB initialization failed: {init_error}")
            raise StorageError(
                f"Memory system initialization failed: {init_error}",
                {'persist_directory': self.persist_directory}
            ) from init_error
        except (OSError, IOError) as init_error:
            logging.error(f"Filesystem error during initialization: {init_error}")
            raise StorageError(
                f"Cannot access storage directory: {init_error}",
                {'persist_directory': self.persist_directory}
            ) from init_error
        except Exception as init_error:
            logging.error(f"Unexpected error initializing memory collections: {init_error}")
            raise StorageError(
                f"Memory system initialization failed: {init_error}",
                {'persist_directory': self.persist_directory}
            ) from init_error

        # Initialize core components (these are exposed as public attributes)
        self.importance_scorer = MemoryImportanceScorer(scoring_config)
        self.chunk_manager = ChunkRelationshipManager(self, memory_config.get('chunk_relationships', {}))

        if deduplication_config is None:
            deduplication_config = {'enabled': False}
        self.deduplicator = MemoryDeduplicator(deduplication_config, self.chunk_manager)

        self.query_monitor = QueryPerformanceMonitor(memory_config.get('query_monitoring', {}))
        self.intelligence_system = MemoryIntelligenceSystem(self, memory_config.get('analytics', {}))

        # Initialize services
        self._init_services(memory_config)

    def _init_services(self, memory_config: Dict[str, Any]) -> None:
        """Initialize decomposed services."""
        # Service configuration
        storage_config = {
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'short_term_threshold': self.short_term_threshold,
            'long_term_threshold': self.long_term_threshold,
        }

        maintenance_config = {
            'short_term_max_size': self.short_term_max_size,
        }

        # Create services
        self._routing_service = QueryRoutingService(
            deduplicator=self.deduplicator
        )

        self._storage_service = MemoryStorageService(
            short_term_memory=self.short_term_memory,
            long_term_memory=self.long_term_memory,
            chunk_manager=self.chunk_manager,
            importance_scorer=self.importance_scorer,
            deduplicator=self.deduplicator,
            lifecycle_manager=self.lifecycle_manager,
            config=storage_config
        )

        self._query_service = MemoryQueryService(
            short_term_memory=self.short_term_memory,
            long_term_memory=self.long_term_memory,
            routing_service=self._routing_service,
            importance_scorer=self.importance_scorer,
            chunk_manager=self.chunk_manager,
            query_monitor=self.query_monitor,
            deduplicator=self.deduplicator
        )

        self._maintenance_service = MemoryMaintenanceService(
            short_term_memory=self.short_term_memory,
            storage_service=self._storage_service,
            deduplicator=self.deduplicator,
            config=maintenance_config
        )

        self._update_service = DocumentUpdateService(
            short_term_memory=self.short_term_memory,
            long_term_memory=self.long_term_memory,
            chunk_manager=self.chunk_manager,
            lifecycle_manager=self.lifecycle_manager,
            storage_service=self._storage_service
        )

        self._stats_service = MemoryStatsService(
            short_term_memory=self.short_term_memory,
            long_term_memory=self.long_term_memory,
            query_monitor=self.query_monitor,
            intelligence_system=self.intelligence_system,
            chunk_manager=self.chunk_manager
        )

    # =========================================================================
    # Public API - Core Memory Operations
    # =========================================================================

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
        result = await self._storage_service.add_memory(content, metadata, context, memory_type)

        # Trigger maintenance if needed (after successful add to short_term)
        if result.get("success") and result.get("collection") == "short_term":
            try:
                await self._maintenance_service.maintain_short_term_memory()
            except Exception as maintenance_error:
                logging.warning(f"Memory maintenance failed: {maintenance_error}")

        return result

    async def query_memories(
        self,
        query: str,
        collections: Optional[List[str]] = None,
        k: int = 5,
        use_smart_routing: bool = True
    ) -> Dict[str, Any]:
        """Query across memory collections with deduplication-aware intelligent routing.

        Args:
            query: Search query string
            collections: List of collection names to search (default: smart routing)
            k: Maximum number of results to return
            use_smart_routing: Whether to use deduplication-aware smart routing

        Returns:
            Dictionary containing formatted search results
        """
        return await self._query_service.query_memories(query, collections, k, use_smart_routing)

    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document and all its chunks by document_id.

        Args:
            document_id: The document ID to delete (memory_id or document_id)

        Returns:
            Dictionary with deletion results including chunks removed and collection
        """
        return await self._update_service.delete_document(document_id)

    async def update_document_importance(
        self,
        document_id: str,
        new_importance: float,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a document's importance score and recalculate TTL.

        Args:
            document_id: The document ID to update
            new_importance: New importance score (0.0-1.0)
            reason: Optional reason for the importance change

        Returns:
            Dictionary with update results including old/new scores and TTL tier
        """
        return await self._update_service.update_document_importance(document_id, new_importance, reason)

    async def update_document_content(
        self,
        document_id: str,
        new_content: str,
        new_metadata: Optional[Dict[str, Any]] = None,
        preserve_importance: bool = True
    ) -> Dict[str, Any]:
        """Update a document's content by replacing it.

        Args:
            document_id: The document ID to update
            new_content: The new content for the document
            new_metadata: Optional new metadata
            preserve_importance: If True, preserve the original importance score

        Returns:
            Dictionary with update results
        """
        return await self._update_service.update_document_content(
            document_id, new_content, new_metadata, preserve_importance
        )

    # =========================================================================
    # Public API - Statistics and Analytics
    # =========================================================================

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all memory collections.

        Returns:
            Dictionary with collection statistics
        """
        return self._stats_service.get_collection_stats()

    def get_query_performance_stats(self, time_window: str = 'all') -> Dict[str, Any]:
        """Get query performance statistics.

        Args:
            time_window: Time window for statistics ('hour', 'day', 'week', 'all')

        Returns:
            Query performance statistics
        """
        return self._stats_service.get_query_performance_stats(time_window)

    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """Get comprehensive system analytics with intelligence insights.

        Returns:
            Comprehensive analytics including predictions and recommendations
        """
        return self._stats_service.get_comprehensive_analytics()

    def get_chunk_relationship_stats(self) -> Dict[str, Any]:
        """Get chunk relationship statistics.

        Returns:
            Chunk relationship statistics and health metrics
        """
        return self._stats_service.get_chunk_relationship_stats()

    # =========================================================================
    # Public API - Configuration
    # =========================================================================

    def set_lifecycle_manager(self, lifecycle_manager) -> None:
        """Set the lifecycle manager for TTL and aging functionality.

        Args:
            lifecycle_manager: LifecycleManager instance
        """
        self.lifecycle_manager = lifecycle_manager
        self._storage_service.set_lifecycle_manager(lifecycle_manager)
        self._update_service.set_lifecycle_manager(lifecycle_manager)
        logging.info("Lifecycle manager integrated with hierarchical memory system")
