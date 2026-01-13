from typing import Any, Dict, Optional
from ..memory import HierarchicalMemorySystem
from ..server.errors import create_tool_error, create_success_response, MCPErrorCode

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

# --- Document Management Tools ---
from .management import (
    delete_document_tool, demote_importance_tool, update_document_tool
)


async def add_document_tool(memory_system: HierarchicalMemorySystem, content: str, metadata: Optional[Dict[str, Any]] = None,
                            context: Optional[Dict[str, Any]] = None, language: str = "text", memory_type: str = "auto") -> Dict[str, Any]:
    """Adds a new document (memory entry) to the hierarchical memory system.
    Automatically scores importance and routes to appropriate memory tiers.
    """
    try:
        # Validate inputs
        if not content or not isinstance(content, str):
            return create_tool_error(
                "Content must be a non-empty string",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={"field": "content", "provided_type": type(content).__name__}
            )

        if metadata is not None and not isinstance(metadata, dict):
            return create_tool_error(
                "Metadata must be a dictionary or None",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={"field": "metadata", "provided_type": type(metadata).__name__}
            )

        if memory_type not in ["auto", "short_term", "long_term", "permanent"]:
            return create_tool_error(
                f"Invalid memory_type '{memory_type}'. Must be one of: auto, short_term, long_term, permanent",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={
                    "field": "memory_type",
                    "valid_values": [
                        "auto",
                        "short_term",
                        "long_term",
                        "permanent"]}
            )

        result = await memory_system.add_memory(content, metadata, context, memory_type)

        return create_success_response(
            message="Document added successfully",
            data={
                "document_id": result.get("memory_id"),
                "assigned_tier": result.get("collection"),
                "importance_score": result.get("importance_score"),
                "details": result.get("message")
            }
        )
    except Exception as e:
        return create_tool_error(
            f"Failed to add document: {str(e)}",
            MCPErrorCode.MEMORY_SYSTEM_ERROR,
            original_error=e
        )

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
    'run_advanced_deduplication_tool',
    # Document Management Tools
    'delete_document_tool', 'demote_importance_tool', 'update_document_tool'
]
