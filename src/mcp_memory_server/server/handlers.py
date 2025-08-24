import asyncio
import json
from typing import List, Dict, Any
from fastapi import Request
from fastapi.responses import JSONResponse

from .models import JsonRpcRequest, JsonRpcResponse, JsonRpcError
from .errors import MCPErrorCode, create_error_response


def convert_to_mcp_format(tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert custom tool response to MCP-compliant format.
    
    Args:
        tool_result: Custom tool response dict
        
    Returns:
        MCP-compliant response dict
    """
    # For MCP compliance, return the tool result directly as structured data
    # The MCP specification expects structured responses, not JSON strings
    
    # Check if it's a success/error response
    is_success = tool_result.get('success', True)
    
    if is_success:
        # For successful responses, return the result directly
        # Remove internal 'success' flag as it's not part of MCP spec
        result = tool_result.copy()
        result.pop('success', None)
        return result
    else:
        # For errors, return error structure
        return {
            "error": {
                "code": -32000,
                "message": tool_result.get('message', 'Tool execution failed'),
                "data": tool_result
            }
        }


async def list_resources_handler() -> List[dict]:
    """Conceptually lists documents in the vector store as resources."""
    return [
        {"id": "doc_123", "name": "Project README", "type": "text/markdown"},
        {"id": "doc_456", "name": "main.py", "type": "text/x-python"},
    ]


async def read_resource_handler(resource_id: str) -> dict:
    """Conceptually reads a specific document from the vector store."""
    if resource_id == "doc_123":
        return {"content": "# Project Title\nThis is the project README file..."}
    elif resource_id == "doc_456":
        return {"content": "import os\n\nprint('hello world')"}
    else:
        raise ValueError(f"Resource '{resource_id}' not found.")


async def event_generator():
    """
    Handles the SSE connection for the Gemini CLI.
    Sends the 'mcp-ready' event and then keeps the connection alive with heartbeats.
    """
    yield "event: mcp-ready\ndata: {}\n\n"

    try:
        while True:
            await asyncio.sleep(10)
            yield "data: heartbeat\n\n"
    except asyncio.CancelledError:
        pass


async def handle_initialize(rpc_id: int, server_config: dict, tool_definitions: List[dict]) -> JSONResponse:
    """Handle MCP initialize request."""
    response = JsonRpcResponse(
        id=rpc_id,
        result={
            "protocolVersion": server_config.get('protocol_version', '2025-06-18'),
            "capabilities": {
                "tools": {},
                "resources": {}
            },
            "serverInfo": {
                "name": server_config.get('title', 'Advanced Project Memory MCP Server'),
                "version": server_config.get('version', '2.0.0'),
                "serverURL": f"http://{server_config.get('host', '127.0.0.1')}:{server_config.get('port', 8080)}/"
            },
            "tools": tool_definitions
        }
    )
    return JSONResponse(content=response.dict(), media_type="application/json-rpc")


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
    """Handle resources/read request."""
    resource_id = params.get("resourceId")
    if not resource_id:
        raise ValueError("`resourceId` parameter is required for `resources/read`.")
    
    content = await read_resource_handler(resource_id)
    response = JsonRpcResponse(id=rpc_id, result=content)
    return JSONResponse(content=response.dict(), media_type="application/json-rpc")


async def handle_tools_call(rpc_id: int, params: dict, tool_registry: Dict[str, Any]) -> JSONResponse:
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
        import asyncio
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
                    "data": {"tool_name": tool_name, "provided_args": list(tool_args.keys())}
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
                "available_methods": ["initialize", "tools/list", "tools/call", "resources/list", "resources/read"]
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