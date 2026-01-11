"""
Memory Services Module

Provides decomposed services for the HierarchicalMemorySystem:
- MemoryStorageService: Document storage operations
- QueryRoutingService: Smart query routing
- MemoryQueryService: Search and retrieval
- MemoryMaintenanceService: Cleanup operations
- DocumentUpdateService: CRUD operations
- MemoryStatsService: Statistics aggregation
- HierarchicalMemorySystem: Facade for backward compatibility
"""

from .storage import MemoryStorageService
from .routing import QueryRoutingService
from .query import MemoryQueryService
from .maintenance import MemoryMaintenanceService
from .update import DocumentUpdateService
from .stats import MemoryStatsService
from .facade import HierarchicalMemorySystem

__all__ = [
    'MemoryStorageService',
    'QueryRoutingService',
    'MemoryQueryService',
    'MemoryMaintenanceService',
    'DocumentUpdateService',
    'MemoryStatsService',
    'HierarchicalMemorySystem',
]
