import logging
import os
from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder

from ..memory import HierarchicalMemorySystem, LifecycleManager
from ..deduplication import MemoryDeduplicator
from ..analytics import MemoryIntelligenceSystem

# --- Document Management Tools ---
from .query import query_documents_tool, apply_reranking

# --- System Monitoring Tools ---
from .stats import get_memory_stats_tool, get_system_health_tool
from .lifecycle import (
    get_lifecycle_stats_tool, cleanup_expired_memories_tool,
    refresh_memory_aging_tool, start_background_maintenance_tool,
    stop_background_maintenance_tool
)
from .permanence import (
    query_permanent_documents_tool, get_permanence_stats_tool
)

# --- Deduplication Tools ---
from .deduplication import (
    deduplicate_memories_tool, get_deduplication_stats_tool, preview_duplicates_tool
)

# --- Performance Monitoring Tools ---
from .performance import (
    get_query_performance_tool, get_real_time_metrics_tool, export_performance_data_tool
)

# --- Analytics and Intelligence Tools ---
from .analytics import (
    get_comprehensive_analytics_tool, get_system_intelligence_tool, 
    get_optimization_recommendations_tool, get_predictive_insights_tool,
    get_chunk_relationships_tool, get_system_health_assessment_tool
)

# --- Advanced Deduplication Tools ---
from .advanced_deduplication import (
    optimize_deduplication_thresholds_tool, get_domain_analysis_tool,
    get_clustering_analysis_tool, get_advanced_deduplication_metrics_tool,
    run_advanced_deduplication_tool
)

async def add_document_tool(memory_system: HierarchicalMemorySystem, content: str, metadata: dict = None, context: dict = None, language: str = "text", memory_type: str = "auto") -> dict:
    """Adds a new document (memory entry) to the hierarchical memory system.
    Automatically scores importance and routes to appropriate memory tiers.
    """
    try:
        result = await memory_system.add_memory(content, metadata, context, memory_type)
        return {
            "status": "success",
            "document_id": result.get("memory_id"),
            "assigned_tier": result.get("collection"),
            "importance_score": result.get("importance_score"),
            "message": result.get("message")
        }
    except Exception as e:
        logging.error(f"Error adding document: {e}")
        return {"status": "error", "message": str(e)}

# Re-add __all__ for proper module export
__all__ = [
    'add_document_tool',
    'query_documents_tool', 'apply_reranking',
    'get_memory_stats_tool', 'get_system_health_tool',
    'get_lifecycle_stats_tool', 'cleanup_expired_memories_tool',
    'refresh_memory_aging_tool', 'start_background_maintenance_tool',
    'stop_background_maintenance_tool',
    'query_permanent_documents_tool', 'get_permanence_stats_tool',
    'deduplicate_memories_tool', 'get_deduplication_stats_tool', 'preview_duplicates_tool',
    'get_query_performance_tool', 'get_real_time_metrics_tool', 'export_performance_data_tool',
    'get_comprehensive_analytics_tool', 'get_system_intelligence_tool',
    'get_optimization_recommendations_tool', 'get_predictive_insights_tool',
    'get_chunk_relationships_tool', 'get_system_health_assessment_tool',
    'optimize_deduplication_thresholds_tool', 'get_domain_analysis_tool',
    'get_clustering_analysis_tool', 'get_advanced_deduplication_metrics_tool',
    'run_advanced_deduplication_tool'
]