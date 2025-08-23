import asyncio
import json
from typing import List, Dict, Any
from fastapi import Request
from fastapi.responses import JSONResponse

from .models import JsonRpcRequest, JsonRpcResponse, JsonRpcError


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
    """Handle tools/call request."""
    tool_name = params.get("name")
    tool_args = params.get("arguments", {})
    
    tool_func = tool_registry.get(tool_name)
    if not tool_func:
        error_response = JsonRpcError(
            id=rpc_id,
            error={
                "code": -32601,
                "message": f"Tool '{tool_name}' not found."
            }
        )
        return JSONResponse(content=error_response.dict(), status_code=400)
    
    # Handle both sync and async tool functions
    import asyncio
    if asyncio.iscoroutinefunction(tool_func):
        result = await tool_func(**tool_args)
    else:
        result = tool_func(**tool_args)
    
    # Convert custom tool response to MCP-compliant format
    mcp_result = convert_to_mcp_format(result)
    
    response = JsonRpcResponse(id=rpc_id, result=mcp_result)
    return JSONResponse(content=response.dict(), media_type="application/json-rpc")


def handle_unknown_method(rpc_id: int, method: str) -> JSONResponse:
    """Handle unknown method requests."""
    error_response = JsonRpcError(
        id=rpc_id,
        error={
            "code": -32601,
            "message": f"Method '{method}' not found."
        }
    )
    return JSONResponse(content=error_response.dict(), status_code=400)


def handle_server_error(rpc_id: int, error: Exception) -> JSONResponse:
    """Handle server errors."""
    error_response = JsonRpcError(
        id=rpc_id,
        error={
            "code": -32000,
            "message": f"An unexpected error occurred: {str(error)}"
        }
    )
    return JSONResponse(content=error_response.dict(), status_code=500)