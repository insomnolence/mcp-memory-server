import logging
from functools import partial
from sentence_transformers import CrossEncoder

from mcp_memory_server.config import Config
from mcp_memory_server.memory import HierarchicalMemorySystem, LifecycleManager
from mcp_memory_server.server import create_app, setup_json_rpc_handler, get_tool_definitions
from mcp_memory_server.tools import (
    add_document_tool, legacy_add_document_tool,
    query_documents_tool, apply_reranking,
    get_memory_stats_tool, get_lifecycle_stats_tool,
    start_background_maintenance_tool, stop_background_maintenance_tool,
    query_permanent_documents_tool, get_permanence_stats_tool
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
        scoring_config=config.get_memory_scoring_config()
    )
    
    # Initialize lifecycle manager (Phase 3)
    lifecycle_manager = LifecycleManager(memory_system, config.get_lifecycle_config())
    
    # Initialize reranker
    reranker_config = config.get_reranker_config()
    reranker_model = CrossEncoder(reranker_config.get('model_name', 'cross-encoder/ms-marco-MiniLM-L-6-v2'))
    
    # Legacy vectorstore for backward compatibility
    vectorstore = memory_system.legacy_memory
    
    # Create tool registry with dependency injection
    tool_registry = {
        "add_document": partial(add_document_tool, memory_system),
        "query_documents": partial(query_documents_with_reranking, memory_system, reranker_model),
        "get_memory_stats": partial(get_memory_stats_tool, memory_system),
        "legacy_add_document": partial(legacy_add_document_tool, vectorstore, config),
        # Phase 3: Lifecycle Management Tools
        "get_lifecycle_stats": partial(get_lifecycle_stats_tool, lifecycle_manager),
        "start_background_maintenance": partial(start_background_maintenance_tool, lifecycle_manager),
        "stop_background_maintenance": partial(stop_background_maintenance_tool, lifecycle_manager),
        # Phase 3.5: Permanence Management Tools
        "query_permanent_documents": partial(query_permanent_documents_tool, memory_system),
        "get_permanence_stats": partial(get_permanence_stats_tool, memory_system),
    }
    
    # Get tool definitions
    tool_definitions = get_tool_definitions()
    
    # Create and configure FastAPI app
    server_config = config.get_server_config()
    app = create_app(server_config)
    
    # Setup JSON-RPC handler
    setup_json_rpc_handler(app, tool_registry, tool_definitions, server_config)
    
    logging.info("Enhanced MCP Server with Lifecycle Management initialized successfully")
    logging.info(f"Phase 3 Features: TTL Management, Memory Aging, Background Maintenance")
    return app


def query_documents_with_reranking(memory_system, reranker_model, query: str, collections: str = None, k: int = 5, use_reranker: bool = True) -> dict:
    """Query documents with reranking support."""
    # Reranking is now handled inside query_documents_tool, so just call it directly
    return query_documents_tool(memory_system, query, collections, k, use_reranker, reranker_model)


# Global app instance for ASGI servers
app = main()

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