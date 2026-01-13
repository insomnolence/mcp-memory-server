from fastapi import FastAPI, Request, Response, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, List, Any, Optional, AsyncIterator
from contextlib import asynccontextmanager
import time
import logging
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError

from .models import JsonRpcRequest
from .handlers import (
    event_generator, handle_initialize, handle_tools_list,
    handle_resources_list, handle_resources_read, handle_tools_call,
    handle_unknown_method, handle_server_error, active_sessions
)
from .errors import MCPErrorCode, create_error_response


async def validate_session_id(mcp_session_id: Optional[str] = Header(None)) -> str:
    if mcp_session_id is None:
        raise HTTPException(status_code=400, detail="Mcp-Session-Id header is required")
    if mcp_session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Invalid or expired Mcp-Session-Id")
    # Update last accessed time
    active_sessions[mcp_session_id]["last_accessed_at"] = time.time()
    return mcp_session_id


async def authenticate_api_key(x_api_key: Optional[str] = Header(None), server_config: Optional[Dict[str, Any]] = None) -> bool:
    """Validate API key if configured.

    If no API key is configured in server_config, authentication is bypassed.
    This is acceptable for development and local-only deployments.
    """
    if server_config is None:
        raise HTTPException(status_code=500, detail="Server configuration not provided for authentication")

    expected_api_key = server_config.get("api_key")
    if not expected_api_key:
        # No API key configured - bypass authentication silently
        # This is logged once at startup, not per-request
        return True

    if x_api_key != expected_api_key:
        logging.warning("API key validation failed")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True


async def validate_accept_header(request: Request) -> None:
    accept_header = request.headers.get("Accept")
    if request.method == "POST":
        # Allow application/json, */* (wildcard), or missing header for MCP compatibility
        if accept_header and "application/json" not in accept_header and "*/*" not in accept_header:
            raise HTTPException(status_code=406, detail="Accept header must include 'application/json' or '*/*'")
    elif request.method == "GET":
        if not accept_header or "text/event-stream" not in accept_header:
            raise HTTPException(status_code=406, detail="Accept header must include 'text/event-stream'")


def create_app(
    server_config: Dict[str, Any],
    lifecycle_manager: Any = None,
    tool_definitions: Optional[List[Dict[str, Any]]] = None,
    active_sessions: Optional[Dict[str, Any]] = None,
    tool_registry: Optional[Dict[str, Any]] = None
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        server_config: Server configuration dictionary
        lifecycle_manager: Lifecycle manager for shutdown cleanup
        tool_definitions: List of tool definition dictionaries for initialize
        active_sessions: Dictionary for active sessions for initialize
        tool_registry: Dictionary mapping tool names to functions

    Returns:
        Configured FastAPI application instance
    """

    # Define lifespan context manager for cleanup
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logging.error(
            "FastAPI Request Validation Error: %s for URL: %s, Body: %s",
            exc.errors(), request.url, await request.body()
        )
        return JSONResponse(
            status_code=422,
            content=create_error_response(
                code=MCPErrorCode.INVALID_REQUEST,
                message=f"Request validation error: {exc.errors()}"
            )
        )

    # Wrapper for authenticate_api_key to resolve RuntimeWarning
    async def get_authenticated_status(x_api_key: Optional[str] = Header(None)) -> bool:
        return await authenticate_api_key(x_api_key, server_config=server_config)

    # Add root endpoint
    @app.api_route("/", methods=["GET", "POST", "DELETE"], response_class=JSONResponse)
    async def root(request: Request, authenticated: bool = Depends(get_authenticated_status)) -> Any:
        """Root endpoint - handles SSE connections, JSON-RPC requests, and disconnections."""
        if request.method == "GET":
            accept = request.headers.get("accept", "")
            if "text/event-stream" in accept.lower():
                logging.info("Root GET requested event stream; returning SSE channel")
                return StreamingResponse(event_generator(), media_type="text/event-stream")
            return {
                "message": "Welcome to the MCP Memory Server!",
                "version": server_config.get('version', '2.0.0'),
                "docs": "/docs"
            }
        elif request.method == "DELETE":
            # Handle Codex cleanup/disconnect
            logging.info("Received DELETE request on root (client disconnect/cleanup)")
            return Response(status_code=200)
        elif request.method == "POST":
            rpc_id = None
            try:
                body = await request.json()
                rpc_request = JsonRpcRequest(**body)
                method = rpc_request.method
                rpc_id = rpc_request.id

                if rpc_id is None:
                    # Notification - no response expected
                    return Response(status_code=202)  # 202 Accepted - required by Codex MCP client

                if method == "initialize":
                    params = rpc_request.params or {}
                    return await handle_initialize(rpc_id, params, server_config, tool_definitions or [], active_sessions or {})  # type: ignore[arg-type]
                elif method == "tools/list":
                    return await handle_tools_list(rpc_id, tool_definitions or [])  # type: ignore[arg-type]
                elif method == "resources/list":
                    return await handle_resources_list(rpc_id)
                elif method == "resources/read":
                    params = rpc_request.params or {}
                    return await handle_resources_read(rpc_id, params)
                elif method == "tools/call":
                    params = rpc_request.params or {}
                    if tool_registry is None:
                        logging.error("tool_registry is None in root endpoint")
                        return handle_unknown_method(rpc_id, "tools/call")
                    return await handle_tools_call(rpc_id, params, tool_registry)
                else:
                    return handle_unknown_method(rpc_id, method)

            except ValidationError as ve:
                logging.error("Pydantic validation error for POST to root: %s, Request body: %s", ve.errors(), body)
                return JSONResponse(
                    content=create_error_response(
                        code=MCPErrorCode.INVALID_REQUEST,
                        message=f"Invalid JSON-RPC request format: {ve.errors()}"
                    ),
                    status_code=422
                )
            except Exception as e:
                error_id: int = rpc_id if 'rpc_id' in locals() and rpc_id is not None else 0
                logging.error("Error handling POST to root: %s, Request body: %s", e, await request.body())
                return handle_server_error(error_id, e)

    # Add health check endpoint
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint for monitoring system status."""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "MCP Memory Server",
            "version": server_config.get('version', '2.0.0')
        }

    return app


def setup_json_rpc_handler(
        app: FastAPI, tool_registry: Dict[str, Any], tool_definitions: List[Dict[str, Any]], server_config: Dict[str, Any]) -> None:
    """Setup the main JSON-RPC and SSE endpoint handler.

    Args:
        app: FastAPI application instance
        tool_registry: Dictionary mapping tool names to functions
        tool_definitions: List of tool definition dictionaries
        server_config: Server configuration dictionary
    """

    @app.get("/mcp")
    async def events_endpoint() -> StreamingResponse:
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.api_route("/mcp", methods=["GET", "POST"], response_class=JSONResponse)
    async def json_rpc_handler(
        request: Request,
        mcp_session_id: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None),
        accept_header_validated: None = Depends(validate_accept_header),
    ) -> Any:
        # Authenticate (no-op when auth disabled)
        await authenticate_api_key(x_api_key, server_config=server_config)

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

                # Only require session validation for stateful operations (tools/call)
                # Discovery methods (tools/list, resources/list, resources/read) do NOT require sessions per MCP spec
                if method == "tools/call":
                    await validate_session_id(mcp_session_id)

                if rpc_id is None:
                    # Notification - no response expected
                    return Response(status_code=202)  # 202 Accepted - required by Codex MCP client

                if method == "initialize":
                    params = rpc_request.params or {}
                    return await handle_initialize(rpc_id, params, server_config, tool_definitions, active_sessions)

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

            except HTTPException as exc:
                # Re-raise FastAPI HTTP errors so the framework can render them
                raise exc
            except Exception as e:
                error_id_val: int = rpc_id if 'rpc_id' in locals() and rpc_id is not None else 0
                return handle_server_error(error_id_val, e)
