import os
import logging
from functools import partial
from sentence_transformers import CrossEncoder

from .config import Config
from .memory import HierarchicalMemorySystem, LifecycleManager
from .server import create_app, setup_json_rpc_handler, get_tool_definitions
from .tools import (
    add_document_tool,
    query_documents_tool,
    get_memory_stats_tool, get_lifecycle_stats_tool,
    start_background_maintenance_tool, stop_background_maintenance_tool, cleanup_expired_memories_tool,
    query_permanent_documents_tool, get_permanence_stats_tool,
    deduplicate_memories_tool, get_deduplication_stats_tool, preview_duplicates_tool,
    get_query_performance_tool, get_real_time_metrics_tool, export_performance_data_tool,
    get_comprehensive_analytics_tool, get_system_intelligence_tool,
    get_optimization_recommendations_tool, get_predictive_insights_tool,
    get_chunk_relationships_tool, get_system_health_assessment_tool,
    optimize_deduplication_thresholds_tool, get_domain_analysis_tool,
    get_clustering_analysis_tool, get_advanced_deduplication_metrics_tool,
    run_advanced_deduplication_tool,
    # Document Management Tools
    delete_document_tool, demote_importance_tool, update_document_tool
)


def main():
    """Main function to initialize and run the refactored MCP server."""
    # Configure logging - force reconfiguration even if logging was already initialized
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '..', '..', 'logs', 'dollhouse_mcp_memory.log')

    # Get root logger and clear existing handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove all existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(file_handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console_handler)

    logging.info("=== MCP Memory Server Starting ===")
    logging.info(f"Log file: {log_file_path}")

    # Initialize configuration - check for environment variable first
    config_path = os.environ.get('MCP_CONFIG_FILE')
    config = Config(config_path=config_path)

    # Log authentication status once at startup
    server_config = config.get_server_config()
    if not server_config.get("api_key"):
        logging.info("API key authentication: DISABLED (no api_key in config)")
    else:
        logging.info("API key authentication: ENABLED")

    # Initialize hierarchical memory system
    memory_system = HierarchicalMemorySystem(
        db_config=config.get_database_config(),
        embeddings_config=config.get_embeddings_config(),
        memory_config=config.get_memory_management_config(),
        scoring_config=config.get_memory_scoring_config(),
        deduplication_config=config.get_deduplication_config()
    )

    # Initialize lifecycle manager (Phase 3)
    lifecycle_manager = LifecycleManager(memory_system, config.get_lifecycle_config())

    # Integrate lifecycle manager with memory system for TTL functionality
    memory_system.set_lifecycle_manager(lifecycle_manager)

    # Auto-start background maintenance (runs overdue tasks including stale ref cleanup)
    lifecycle_manager.start_background_maintenance()

    # Initialize reranker
    reranker_config = config.get_reranker_config()
    reranker_model = CrossEncoder(reranker_config.get('model_name', 'cross-encoder/ms-marco-MiniLM-L-6-v2'))

    # Create tool registry with dependency injection
    tool_registry = {
        "add_document": partial(add_document_tool, memory_system),
        "query_documents": partial(query_documents_with_reranking, memory_system, reranker_model),
        "get_memory_stats": partial(get_memory_stats_tool, memory_system),
        # Phase 3: Lifecycle Management Tools
        "get_lifecycle_stats": partial(get_lifecycle_stats_tool, lifecycle_manager),
        "start_background_maintenance": partial(start_background_maintenance_tool, lifecycle_manager),
        "stop_background_maintenance": partial(stop_background_maintenance_tool, lifecycle_manager),
        "cleanup_expired_memories": partial(cleanup_expired_memories_tool, lifecycle_manager),
        # Phase 3.5: Permanence Management Tools
        "query_permanent_documents": partial(query_permanent_documents_tool, memory_system),
        "get_permanence_stats": partial(get_permanence_stats_tool, memory_system),
        # Phase 1: Deduplication Management Tools
        "deduplicate_memories": partial(deduplicate_memories_tool, memory_system),
        "get_deduplication_stats": partial(get_deduplication_stats_tool, memory_system),
        "preview_duplicates": partial(preview_duplicates_tool, memory_system),
        # Phase 2: Performance Monitoring Tools
        "get_query_performance": partial(get_query_performance_tool, memory_system),
        "get_real_time_metrics": partial(get_real_time_metrics_tool, memory_system),
        "export_performance_data": partial(export_performance_data_tool, memory_system),
        # Phase 3: Analytics and Intelligence Tools
        "get_comprehensive_analytics": partial(get_comprehensive_analytics_tool, memory_system),
        "get_system_intelligence": partial(get_system_intelligence_tool, memory_system),
        "get_optimization_recommendations": partial(get_optimization_recommendations_tool, memory_system),
        "get_predictive_insights": partial(get_predictive_insights_tool, memory_system),
        "get_chunk_relationships": partial(get_chunk_relationships_tool, memory_system),
        "get_system_health_assessment": partial(get_system_health_assessment_tool, memory_system),
        # Phase 3: Advanced Deduplication Tools
        "optimize_deduplication_thresholds": partial(optimize_deduplication_thresholds_tool, memory_system),
        "get_domain_analysis": partial(get_domain_analysis_tool, memory_system),
        "get_clustering_analysis": partial(get_clustering_analysis_tool, memory_system),
        "get_advanced_deduplication_metrics": partial(get_advanced_deduplication_metrics_tool, memory_system),
        "run_advanced_deduplication": partial(run_advanced_deduplication_tool, memory_system),
        # Document Management Tools
        "delete_document": partial(delete_document_tool, memory_system),
        "demote_importance": partial(demote_importance_tool, memory_system, lifecycle_manager),
        "update_document": partial(update_document_tool, memory_system),
    }

    # Get tool definitions
    tool_definitions = get_tool_definitions()

    # Create and configure FastAPI app
    server_config = config.get_server_config()
    # Import active_sessions from handlers to pass to create_app
    from .server.handlers import active_sessions
    app = create_app(server_config, lifecycle_manager, tool_definitions, active_sessions, tool_registry)

    # Setup JSON-RPC handler
    setup_json_rpc_handler(app, tool_registry, tool_definitions, server_config)
    logging.info("Enhanced MCP Server with Lifecycle Management initialized successfully")
    logging.info("Phase 3 Features: TTL Management, Memory Aging, Background Maintenance")
    return app


async def query_documents_with_reranking(memory_system, reranker_model, query: str,
                                         collections: str = None, k: int = 5, use_reranker: bool = True) -> dict:
    """Query documents with reranking support."""
    # Reranking is now handled inside query_documents_tool, so just call it directly
    return await query_documents_tool(memory_system, query, collections, k, use_reranker, reranker_model)


# Global variables for cleanup
_global_app = None

# Initialize app


def get_app(config_path=None):
    """Get or create the FastAPI app instance."""
    global _global_app
    if _global_app is None:
        # Set environment variable if provided
        if config_path:
            os.environ['MCP_CONFIG_FILE'] = config_path
        _global_app = main()
    return _global_app


# Global app instance for ASGI servers - check for environment config
config_path = os.environ.get('MCP_CONFIG_FILE')
app = get_app(config_path=config_path)

if __name__ == "__main__":
    import uvicorn

    config_path = os.environ.get('MCP_CONFIG_FILE')
    config = Config(config_path=config_path)
    server_config = config.get_server_config()

    uvicorn.run(
        "mcp_memory_server.main:app",
        host=server_config.get('host', '127.0.0.1'),
        port=server_config.get('port', 8080),
        reload=True
    )
