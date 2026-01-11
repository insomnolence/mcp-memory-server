from .scorer import MemoryImportanceScorer
# Import from new decomposed services (facade maintains backward compatibility)
from .services import HierarchicalMemorySystem
from .lifecycle import LifecycleManager, TTLManager, MemoryAging

# Re-export services for direct access if needed
from .services import (
    MemoryStorageService,
    QueryRoutingService,
    MemoryQueryService,
    MemoryMaintenanceService,
    DocumentUpdateService,
    MemoryStatsService,
)

__all__ = [
    # Main classes
    'MemoryImportanceScorer',
    'HierarchicalMemorySystem',
    'LifecycleManager',
    'TTLManager',
    'MemoryAging',
    # Decomposed services
    'MemoryStorageService',
    'QueryRoutingService',
    'MemoryQueryService',
    'MemoryMaintenanceService',
    'DocumentUpdateService',
    'MemoryStatsService',
]
