from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, List, Any
from contextlib import asynccontextmanager
import time
import logging

from .models import JsonRpcRequest
from .handlers import (
    event_generator, handle_initialize, handle_tools_list, 
    handle_resources_list, handle_resources_read, handle_tools_call,
    handle_unknown_method, handle_server_error
)
from .errors import MCPErrorCode, create_error_response


def create_app(server_config: dict, lifecycle_manager=None) -> FastAPI:
    """Create and configure the FastAPI application.
    
    Args:
        server_config: Server configuration dictionary
        lifecycle_manager: Lifecycle manager for shutdown cleanup
        
    Returns:
        Configured FastAPI application instance
    """
    
    # Define lifespan context manager for cleanup
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logging.info("FastAPI application starting up")
        yield
        # Shutdown
        if lifecycle_manager:
            logging.info("FastAPI shutdown: stopping background maintenance")
            if hasattr(lifecycle_manager, 'stop_background_maintenance'):
                lifecycle_manager.stop_background_maintenance()
            logging.info("Lifecycle cleanup completed")
    
    # Create app with lifespan if lifecycle_manager is provided
    if lifecycle_manager:
        app = FastAPI(
            title=server_config.get('title', 'Advanced Project Memory MCP Server'),
            version=server_config.get('version', '2.0.0'),
            lifespan=lifespan
        )
    else:
        app = FastAPI(
            title=server_config.get('title', 'Advanced Project Memory MCP Server'),
            version=server_config.get('version', '2.0.0')
        )
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring system status."""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "MCP Memory Server",
            "version": server_config.get('version', '2.0.0')
        }
    
    return app


def setup_json_rpc_handler(app: FastAPI, tool_registry: Dict[str, Any], tool_definitions: List[dict], server_config: dict):
    """Setup the main JSON-RPC and SSE endpoint handler.
    
    Args:
        app: FastAPI application instance
        tool_registry: Dictionary mapping tool names to functions
        tool_definitions: List of tool definition dictionaries
        server_config: Server configuration dictionary
    """
    
    @app.api_route("/", methods=["GET", "POST"], response_class=JSONResponse)
    async def json_rpc_handler(request: Request):
        if request.method == "GET":
            return StreamingResponse(event_generator(), media_type="text/event-stream")

        if request.method == "POST":
            rpc_id = None
            try:
                # Parse JSON body
                try:
                    body = await request.json()
                except Exception as e:
                    # JSON parsing error - return parse error
                    error_response = create_error_response(
                        code=MCPErrorCode.PARSE_ERROR,
                        message=f"Invalid JSON: {str(e)}"
                    )
                    return JSONResponse(
                        content={"jsonrpc": "2.0", "id": None, "error": error_response["error"]},
                        status_code=400
                    )
                
                # Validate JSON-RPC request structure
                try:
                    rpc_request = JsonRpcRequest(**body)
                except Exception as e:
                    # Invalid request structure
                    error_response = create_error_response(
                        code=MCPErrorCode.INVALID_REQUEST,
                        message=f"Invalid request structure: {str(e)}"
                    )
                    return JSONResponse(
                        content={"jsonrpc": "2.0", "id": body.get("id"), "error": error_response["error"]},
                        status_code=400
                    )
                
                method = rpc_request.method
                rpc_id = rpc_request.id

                if rpc_id is None:
                    if method == "notifications/initialized":
                        print("Received 'notifications/initialized' from client.")
                    return

                if method == "initialize":
                    return await handle_initialize(rpc_id, server_config, tool_definitions)

                elif method == "tools/list":
                    return await handle_tools_list(rpc_id, tool_definitions)
                
                elif method == "resources/list":
                    return await handle_resources_list(rpc_id)
                
                elif method == "resources/read":
                    params = rpc_request.params or {}
                    return await handle_resources_read(rpc_id, params)

                elif method == "tools/call":
                    params = rpc_request.params or {}
                    return await handle_tools_call(rpc_id, params, tool_registry)

                else:
                    return handle_unknown_method(rpc_id, method)

            except Exception as e:
                error_id = rpc_id if 'rpc_id' in locals() and rpc_id is not None else None
                return handle_server_error(error_id, e)