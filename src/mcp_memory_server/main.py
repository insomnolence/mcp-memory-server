import logging
from functools import partial
from sentence_transformers import CrossEncoder

from mcp_memory_server.config import Config
from mcp_memory_server.memory import HierarchicalMemorySystem, LifecycleManager
from mcp_memory_server.server import create_app, setup_json_rpc_handler, get_tool_definitions
from mcp_memory_server.tools import (
    add_document_tool,
    query_documents_tool, apply_reranking,
    get_memory_stats_tool, get_lifecycle_stats_tool,
    start_background_maintenance_tool, stop_background_maintenance_tool,
    query_permanent_documents_tool, get_permanence_stats_tool,
    deduplicate_memories_tool, get_deduplication_stats_tool, preview_duplicates_tool,
    get_query_performance_tool, get_real_time_metrics_tool, export_performance_data_tool
)


def main():
    """Main function to initialize and run the refactored MCP server."""
    # Initialize configuration
    config = Config()
    
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
    }
    
    # Get tool definitions
    tool_definitions = get_tool_definitions()
    
    # Create and configure FastAPI app
    server_config = config.get_server_config()
    app = create_app(server_config, lifecycle_manager)
    
    # Setup JSON-RPC handler
    setup_json_rpc_handler(app, tool_registry, tool_definitions, server_config)
    
    logging.info("Enhanced MCP Server with Lifecycle Management initialized successfully")
    logging.info(f"Phase 3 Features: TTL Management, Memory Aging, Background Maintenance")
    return app


def query_documents_with_reranking(memory_system, reranker_model, query: str, collections: str = None, k: int = 5, use_reranker: bool = True) -> dict:
    """Query documents with reranking support."""
    # Reranking is now handled inside query_documents_tool, so just call it directly
    return query_documents_tool(memory_system, query, collections, k, use_reranker, reranker_model)


# Global variables for cleanup
_global_app = None

# Initialize app
def get_app():
    """Get or create the FastAPI app instance."""
    global _global_app
    if _global_app is None:
        _global_app = main()
    return _global_app

# Global app instance for ASGI servers
app = get_app()

if __name__ == "__main__":
    import uvicorn
    
    config = Config()
    server_config = config.get_server_config()
    
    uvicorn.run(
        "mcp_memory_server.main:app",
        host=server_config.get('host', '127.0.0.1'),
        port=server_config.get('port', 8080),
        reload=True
    )