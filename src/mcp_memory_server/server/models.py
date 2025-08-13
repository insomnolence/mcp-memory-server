from pydantic import BaseModel
from typing import Dict, Any, Optional


class JsonRpcRequest(BaseModel):
    """JSON-RPC request model."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC response model."""
    jsonrpc: str = "2.0"
    id: Optional[int]
    result: Any


class JsonRpcError(BaseModel):
    """JSON-RPC error response model."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    error: Dict[str, Any]