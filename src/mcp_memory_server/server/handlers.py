import asyncio
import json
import uuid
import time
from typing import List, Dict, Any
from fastapi.responses import JSONResponse

from .models import JsonRpcResponse, JsonRpcError
from .errors import MCPErrorCode

# In-memory storage for active sessions (for demonstration purposes)
active_sessions: Dict[str, Dict[str, Any]] = {}


def convert_to_mcp_format(tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert tool response to MCP-compliant format.

    Per MCP 2025-06-18 spec, all tool results must have:
    - content: array of content objects
    - isError: boolean indicating success/failure

    Args:
        tool_result: Tool response dict

    Returns:
        MCP-compliant response dict (already compliant if from our tools)
    """
    # Our tools now return MCP-compliant format with content + isError
    # Just pass through as-is
    return tool_result


async def list_resources_handler() -> List[dict]:
    """List resources following MCP 2025-06-18 specification.

    This memory server uses tools (query_documents, add_document, etc.) for all
    memory operations rather than exposing memories as browsable resources.
    Returns an empty list as there are no static resources to expose.

    Returns:
        Empty list - use query_documents tool for memory access.
    """
    return []


async def read_resource_handler(uri: str) -> dict:
    """Read a resource following MCP 2025-06-18 specification.

    This memory server does not expose resources. Use the query_documents
    tool to search and retrieve memory content instead.

    Raises:
        ValueError: Always, as no resources are available.
    """
    raise ValueError(
        f"Resource '{uri}' not found. This memory server uses tools for "
        "content access. Use 'query_documents' to search memories."
    )


async def event_generator() -> Any:
    """Handle SSE connection for the Gemini CLI.

    Sends the 'mcp-ready' event and keeps the connection alive with heartbeats.
    """
    yield "event: mcp-ready\ndata: {}\n\n"

    try:
        while True:
            await asyncio.sleep(10)
            heartbeat_payload = json.dumps({
                "type": "heartbeat",
                "timestamp": time.time()
            })
            yield f"event: heartbeat\ndata: {heartbeat_payload}\n\n"
    except asyncio.CancelledError:
        pass


async def handle_initialize(
    rpc_id: int,
    params: dict,
    server_config: dict,
    tool_definitions: List[dict],
    active_sessions: Dict[str, Dict[str, Any]]
) -> JSONResponse:
    """Handle MCP initialize request per specification.

    Supports protocol versions: 2024-11-05, 2025-03-26, 2025-06-18
    """
    params = params or {}
    requested_protocol = params.get("protocolVersion")

    # Supported protocol versions (newest first)
    supported_versions = ["2025-06-18", "2025-03-26", "2024-11-05"]
    server_default = server_config.get('protocol_version', "2024-11-05")

    # Protocol version negotiation:
    # 1. If client requests a version we support, use it
    # 2. Otherwise, use our default (client may disconnect if incompatible)
    if requested_protocol and requested_protocol in supported_versions:
        protocol_version = requested_protocol
    else:
        if server_default in supported_versions:
            protocol_version = server_default
        else:
            protocol_version = "2024-11-05"

    # Create session
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        "initialized_at": time.time(),
        "last_accessed_at": time.time(),
        "protocol_version": protocol_version
    }

    # Build MCP-compliant response
    result = {
        "protocolVersion": protocol_version,
        "capabilities": {
            "tools": {},  # Server supports tools (definitions come from tools/list)
            "resources": {}  # Server offers resources capability
        },
        "serverInfo": {
            "name": server_config.get('title', 'Dollhouse MCP Development Memory Server'),
            "version": server_config.get('version', '2.0.0')
        }
        # Tools array removed - per MCP spec, tools come from tools/list, NOT initialize
    }

    response = JsonRpcResponse(id=rpc_id, result=result)

    # Per MCP 2025-06-18 spec: Return session ID in Mcp-Session-Id header
    # This allows the server to track client sessions for stateful operations
    return JSONResponse(
        content=response.dict(),
        media_type="application/json",
        headers={"Mcp-Session-Id": session_id}
    )


async def handle_tools_list(rpc_id: int, tool_definitions: List[dict]) -> JSONResponse:
    """Handle tools/list request."""
    response = JsonRpcResponse(
        id=rpc_id,
        result={
            "tools": tool_definitions
        }
    )
    return JSONResponse(content=response.dict(), media_type="application/json-rpc")


async def handle_resources_list(rpc_id: int) -> JSONResponse:
    """Handle resources/list request."""
    resources = await list_resources_handler()
    response = JsonRpcResponse(id=rpc_id, result={"resources": resources})
    return JSONResponse(content=response.dict(), media_type="application/json-rpc")


async def handle_resources_read(rpc_id: int, params: dict) -> JSONResponse:
    """Handle resources/read request per MCP 2025-06-18 specification."""
    uri = params.get("uri")
    if not uri:
        raise ValueError("`uri` parameter is required for `resources/read`.")

    content = await read_resource_handler(uri)
    response = JsonRpcResponse(id=rpc_id, result=content)
    return JSONResponse(content=response.dict(), media_type="application/json-rpc")


async def handle_tools_call(
    rpc_id: int,
    params: dict,
    tool_registry: Dict[str, Any]
) -> JSONResponse:
    """Handle tools/call request with comprehensive error handling."""
    try:
        # Validate required parameters
        if not isinstance(params, dict):
            error_response = JsonRpcError(
                id=rpc_id,
                error={
                    "code": int(MCPErrorCode.INVALID_PARAMS),
                    "message": "Parameters must be an object",
                    "data": {"provided_type": type(params).__name__}
                }
            )
            return JSONResponse(content=error_response.dict(), status_code=400)

        tool_name = params.get("name")
        if not tool_name:
            error_response = JsonRpcError(
                id=rpc_id,
                error={
                    "code": int(MCPErrorCode.INVALID_PARAMS),
                    "message": "Missing required parameter 'name'",
                    "data": {"required_params": ["name"]}
                }
            )
            return JSONResponse(content=error_response.dict(), status_code=400)

        tool_args = params.get("arguments", {})
        if not isinstance(tool_args, dict):
            error_response = JsonRpcError(
                id=rpc_id,
                error={
                    "code": int(MCPErrorCode.INVALID_PARAMS),
                    "message": "Tool arguments must be an object",
                    "data": {"provided_type": type(tool_args).__name__}
                }
            )
            return JSONResponse(content=error_response.dict(), status_code=400)

        # Check if tool exists
        tool_func = tool_registry.get(tool_name)
        if not tool_func:
            error_response = JsonRpcError(
                id=rpc_id,
                error={
                    "code": int(MCPErrorCode.METHOD_NOT_FOUND),
                    "message": f"Tool '{tool_name}' not found",
                    "data": {
                        "available_tools": list(tool_registry.keys()),
                        "requested_tool": tool_name
                    }
                }
            )
            return JSONResponse(content=error_response.dict(), status_code=404)

        # Execute tool function with error handling
        try:
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**tool_args)
            else:
                result = tool_func(**tool_args)
        except TypeError as e:
            # Parameter validation error
            error_response = JsonRpcError(
                id=rpc_id,
                error={
                    "code": int(MCPErrorCode.INVALID_PARAMS),
                    "message": f"Invalid parameters for tool '{tool_name}': {str(e)}",
                    "data": {
                        "tool_name": tool_name,
                        "provided_args": list(tool_args.keys())
                    }
                }
            )
            return JSONResponse(content=error_response.dict(), status_code=400)
        except Exception as e:
            # Tool execution error
            error_response = JsonRpcError(
                id=rpc_id,
                error={
                    "code": int(MCPErrorCode.TOOL_EXECUTION_ERROR),
                    "message": f"Tool '{tool_name}' execution failed: {str(e)}",
                    "data": {
                        "tool_name": tool_name,
                        "error_type": type(e).__name__
                    }
                }
            )
            return JSONResponse(content=error_response.dict(), status_code=500)

        # Convert custom tool response to MCP-compliant format
        mcp_result = convert_to_mcp_format(result)

        response = JsonRpcResponse(id=rpc_id, result=mcp_result)
        return JSONResponse(content=response.dict(), media_type="application/json-rpc")

    except Exception as e:
        # Unexpected error in handler
        error_response = JsonRpcError(
            id=rpc_id,
            error={
                "code": int(MCPErrorCode.INTERNAL_ERROR),
                "message": f"Internal server error: {str(e)}",
                "data": {"error_type": type(e).__name__}
            }
        )
        return JSONResponse(content=error_response.dict(), status_code=500)


def handle_unknown_method(rpc_id: int, method: str) -> JSONResponse:
    """Handle unknown method requests."""
    error_response = JsonRpcError(
        id=rpc_id,
        error={
            "code": int(MCPErrorCode.METHOD_NOT_FOUND),
            "message": f"Method '{method}' not found",
            "data": {
                "requested_method": method,
                "available_methods": [
                    "initialize",
                    "tools/list",
                    "tools/call",
                    "resources/list",
                    "resources/read"
                ]
            }
        }
    )
    return JSONResponse(content=error_response.dict(), status_code=404)


def handle_server_error(rpc_id: int, error: Exception) -> JSONResponse:
    """Handle server errors."""
    error_response = JsonRpcError(
        id=rpc_id,
        error={
            "code": int(MCPErrorCode.INTERNAL_ERROR),
            "message": f"Internal server error: {str(error)}",
            "data": {
                "error_type": type(error).__name__,
                "server_component": "json_rpc_handler"
            }
        }
    )
    return JSONResponse(content=error_response.dict(), status_code=500)
