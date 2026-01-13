"""
Memory Stats Service

Handles statistics and analytics aggregation including:
- Collection statistics
- Query performance stats
- Comprehensive analytics
- Chunk relationship stats
"""

import logging
from typing import Dict, Any

from langchain_chroma import Chroma


class MemoryStatsService:
    """Service responsible for statistics and analytics aggregation."""

    def __init__(
        self,
        short_term_memory: Chroma,
        long_term_memory: Chroma,
        query_monitor: Any,
        intelligence_system: Any,
        chunk_manager: Any
    ) -> None:
        """Initialize stats service.

        Args:
            short_term_memory: Chroma collection for short-term storage
            long_term_memory: Chroma collection for long-term storage
            query_monitor: QueryPerformanceMonitor instance
            intelligence_system: MemoryIntelligenceSystem instance
            chunk_manager: ChunkRelationshipManager instance
        """
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.query_monitor = query_monitor
        self.intelligence_system = intelligence_system
        self.chunk_manager = chunk_manager

        # Store additional collections for dynamic stats
        self._additional_collections: Dict[str, Chroma] = {}

    def register_collection(self, name: str, collection: Chroma) -> None:
        """Register an additional collection for stats tracking.

        Args:
            name: Collection name
            collection: Chroma collection instance
        """
        self._additional_collections[name] = collection

    def _get_all_collections(self) -> Dict[str, Chroma]:
        """Get all registered collections."""
        collections = {
            'short_term': self.short_term_memory,
            'long_term': self.long_term_memory
        }
        collections.update(self._additional_collections)
        return collections

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all memory collections.

        Returns:
            Dictionary with collection statistics
        """
        stats: Dict[str, Any] = {"collections": {}}

        collections = self._get_all_collections()

        for collection_name, collection in collections.items():
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
            result = self.query_monitor.get_performance_summary(time_window)
            return dict(result) if result else {}
        except Exception as e:
            logging.warning(f"Failed to get query performance stats: {e}")
            return {'error': str(e), 'message': 'Query monitoring not available'}

    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """Get comprehensive system analytics with intelligence insights.

        Returns:
            Comprehensive analytics including predictions and recommendations
        """
        try:
            result = self.intelligence_system.generate_comprehensive_analytics()
            return dict(result) if result else {}
        except Exception as e:
            logging.warning(f"Failed to get comprehensive analytics: {e}")
            return {'error': str(e), 'message': 'Analytics system not available'}

    def get_chunk_relationship_stats(self) -> Dict[str, Any]:
        """Get chunk relationship statistics.

        Returns:
            Chunk relationship statistics and health metrics
        """
        try:
            if self.chunk_manager:
                result = self.chunk_manager.get_relationship_statistics()
                return dict(result) if result else {}
            else:
                return {'error': 'Chunk relationship manager not available'}
        except Exception as e:
            logging.warning(f"Failed to get chunk relationship stats: {e}")
            return {'error': str(e), 'message': 'Chunk relationship tracking not available'}
