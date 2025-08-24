"""
Standard error handling for MCP server with JSON-RPC 2.0 compliance.

This module provides standardized error codes and formatting functions
to ensure all errors are consistently formatted according to the JSON-RPC 2.0 specification.
"""

from enum import IntEnum
from typing import Dict, Any, Optional
import logging


class MCPErrorCode(IntEnum):
    """Standard error codes for MCP server operations.
    
    Based on JSON-RPC 2.0 specification with MCP-specific extensions.
    """
    # JSON-RPC 2.0 standard errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP implementation-defined errors (-32000 to -32099)
    TOOL_EXECUTION_ERROR = -32000
    MEMORY_SYSTEM_ERROR = -32001
    DATABASE_ERROR = -32002
    DEDUPLICATION_ERROR = -32003
    LIFECYCLE_ERROR = -32004
    CONFIGURATION_ERROR = -32005
    VALIDATION_ERROR = -32006
    PERMISSION_ERROR = -32007
    RESOURCE_NOT_FOUND = -32008
    TIMEOUT_ERROR = -32009


def create_error_response(
    code: MCPErrorCode,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    log_error: bool = True
) -> Dict[str, Any]:
    """Create a standardized JSON-RPC 2.0 error response.
    
    Args:
        code: Standard error code from MCPErrorCode
        message: Human-readable error message
        data: Optional additional error data
        log_error: Whether to log the error
        
    Returns:
        Standardized error response dictionary
    """
    if log_error:
        logging.error(f"MCP Error {code}: {message}")
        if data:
            logging.error(f"Error data: {data}")
    
    error_response = {
        "success": False,
        "error": {
            "code": int(code),
            "message": message
        }
    }
    
    if data:
        error_response["error"]["data"] = data
    
    return error_response


def create_tool_error(
    message: str,
    error_code: MCPErrorCode = MCPErrorCode.TOOL_EXECUTION_ERROR,
    original_error: Optional[Exception] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized tool execution error response.
    
    Args:
        message: Human-readable error message
        error_code: Specific error code (defaults to TOOL_EXECUTION_ERROR)
        original_error: Original exception that caused the error
        additional_data: Additional error context data
        
    Returns:
        Standardized error response dictionary
    """
    data = {}
    
    if original_error:
        data["original_error"] = {
            "type": type(original_error).__name__,
            "message": str(original_error)
        }
    
    if additional_data:
        data.update(additional_data)
    
    return create_error_response(
        code=error_code,
        message=message,
        data=data if data else None
    )


def create_validation_error(field: str, value: Any, expected: str) -> Dict[str, Any]:
    """Create a parameter validation error response.
    
    Args:
        field: Name of the invalid field
        value: The invalid value provided
        expected: Description of expected value
        
    Returns:
        Standardized validation error response
    """
    return create_error_response(
        code=MCPErrorCode.VALIDATION_ERROR,
        message=f"Invalid parameter '{field}': expected {expected}",
        data={
            "field": field,
            "provided_value": str(value),
            "expected": expected
        }
    )


def create_not_found_error(resource_type: str, resource_id: str) -> Dict[str, Any]:
    """Create a resource not found error response.
    
    Args:
        resource_type: Type of resource that wasn't found
        resource_id: ID of the resource that wasn't found
        
    Returns:
        Standardized not found error response
    """
    return create_error_response(
        code=MCPErrorCode.RESOURCE_NOT_FOUND,
        message=f"{resource_type} '{resource_id}' not found",
        data={
            "resource_type": resource_type,
            "resource_id": resource_id
        }
    )


def wrap_tool_execution(func):
    """Decorator to wrap tool functions with standardized error handling.
    
    This decorator catches all exceptions and converts them to standardized
    JSON-RPC error responses.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return create_tool_error(
                message=f"Tool execution failed: {str(e)}",
                original_error=e,
                additional_data={
                    "tool_name": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
            )
    
    # Preserve async functions
    if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return create_tool_error(
                    message=f"Tool execution failed: {str(e)}",
                    original_error=e,
                    additional_data={
                        "tool_name": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs)
                    }
                )
        return async_wrapper
    
    return wrapper