# MCP Error Handling

## Overview

The MCP Memory Server implements comprehensive error handling that fully complies with the JSON-RPC 2.0 specification. All errors are consistently formatted and include appropriate error codes, messages, and additional context data.

## Error Codes

The server uses standard JSON-RPC 2.0 error codes plus MCP-specific implementation-defined codes:

### Standard JSON-RPC 2.0 Errors
- `-32700` - Parse error (Invalid JSON)
- `-32600` - Invalid request (Malformed JSON-RPC request)
- `-32601` - Method not found
- `-32602` - Invalid params
- `-32603` - Internal error

### MCP Implementation-Defined Errors (-32000 to -32099)
- `-32000` - Tool execution error
- `-32001` - Memory system error
- `-32002` - Database error
- `-32003` - Deduplication error
- `-32004` - Lifecycle error
- `-32005` - Configuration error
- `-32006` - Validation error
- `-32007` - Permission error
- `-32008` - Resource not found
- `-32009` - Timeout error

## Error Response Format

All errors follow the JSON-RPC 2.0 error response format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32006,
    "message": "Parameter 'k' must be a positive integer",
    "data": {
      "field": "k",
      "provided_value": -1,
      "expected": "positive integer"
    }
  }
}
```

## Tool Error Handling

Tools consistently return error responses in this format:

```json
{
  "success": false,
  "error": {
    "code": -32006,
    "message": "Content must be a non-empty string",
    "data": {
      "field": "content",
      "provided_type": "NoneType"
    }
  }
}
```

## Input Validation

The server performs comprehensive input validation:

- **Parameter type checking**: Ensures parameters are the expected type
- **Required field validation**: Checks for missing required parameters  
- **Range validation**: Validates numeric parameters are within acceptable ranges
- **Enum validation**: Validates parameters against allowed values

## Error Context

Error responses include contextual information:
- **Field names**: Which parameter caused the validation error
- **Expected vs provided**: What was expected vs what was provided
- **Available options**: Valid choices for enum-type parameters
- **Original error details**: Information about underlying exceptions

## Implementation

Error handling is implemented through:
- `src/mcp_memory_server/server/errors.py` - Standardized error creation functions
- Enhanced parameter validation in all tool functions
- Comprehensive exception handling in JSON-RPC handlers
- Consistent error response formatting

This ensures robust, debuggable error handling that helps developers understand and fix issues quickly.