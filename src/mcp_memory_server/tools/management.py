"""Document management tools for the MCP Memory Server.

These tools provide manual control over document lifecycle:
- delete_document: Permanently remove a document
- demote_importance: Lower a document's importance to allow TTL expiry
"""

from typing import Dict, Any
from ..memory import HierarchicalMemorySystem
from ..memory.lifecycle import LifecycleManager
from ..server.errors import create_success_response, create_tool_error, MCPErrorCode


async def delete_document_tool(
    memory_system: HierarchicalMemorySystem,
    document_id: str,
    confirm: bool = False
) -> Dict[str, Any]:
    """Delete a document from the memory system.

    Args:
        memory_system: HierarchicalMemorySystem instance
        document_id: The document ID to delete (memory_id or document_id)
        confirm: Must be True to confirm deletion (safety check)

    Returns:
        Deletion results including chunks removed and collection
    """
    try:
        # Validate inputs
        if not document_id or not isinstance(document_id, str):
            return create_tool_error(
                "Document ID must be a non-empty string",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={"field": "document_id"}
            )

        # Safety check - require explicit confirmation
        if not confirm:
            return create_tool_error(
                "Deletion requires confirm=true. This action cannot be undone.",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={
                    "document_id": document_id,
                    "hint": "Set confirm=true to proceed with deletion"
                }
            )

        # Perform deletion
        result = await memory_system.delete_document(document_id)

        if result.get("success"):
            return create_success_response(
                message=f"Document {document_id} deleted successfully",
                data={
                    "document_id": document_id,
                    "chunks_deleted": result.get("chunks_deleted", 0),
                    "collection": result.get("collection"),
                    "details": result.get("message")
                }
            )
        else:
            return create_tool_error(
                result.get("message", f"Failed to delete document {document_id}"),
                MCPErrorCode.RESOURCE_NOT_FOUND,
                additional_data={"document_id": document_id}
            )

    except Exception as e:
        return create_tool_error(
            f"Failed to delete document: {str(e)}",
            MCPErrorCode.MEMORY_SYSTEM_ERROR,
            original_error=e
        )


async def demote_importance_tool(
    memory_system: HierarchicalMemorySystem,
    lifecycle_manager: LifecycleManager,
    document_id: str,
    new_importance: float = 0.5,
    reason: str = None
) -> Dict[str, Any]:
    """Demote a document's importance score to allow TTL expiry.

    Lowering the importance score moves a document out of the permanent tier,
    allowing it to expire naturally via TTL.

    Args:
        memory_system: HierarchicalMemorySystem instance
        lifecycle_manager: LifecycleManager instance (for TTL recalculation)
        document_id: The document ID to demote
        new_importance: New importance score (0.0-0.94, must be below permanent threshold)
        reason: Optional reason for the demotion (stored in metadata)

    Returns:
        Update results including old/new importance and TTL tier
    """
    try:
        # Validate inputs
        if not document_id or not isinstance(document_id, str):
            return create_tool_error(
                "Document ID must be a non-empty string",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={"field": "document_id"}
            )

        # Validate importance score range (must be below permanent threshold)
        if not (0.0 <= new_importance <= 0.94):
            return create_tool_error(
                "Importance score must be between 0.0 and 0.94 (below permanent threshold)",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={
                    "provided": new_importance,
                    "valid_range": "0.0 - 0.94",
                    "hint": "Use 0.3 for ~1 day TTL, 0.5 for ~3 day TTL, 0.7 for ~1 week TTL"
                }
            )

        # Perform the importance update
        result = await memory_system.update_document_importance(
            document_id, new_importance, reason
        )

        if result.get("success"):
            return create_success_response(
                message=f"Document {document_id} importance demoted successfully",
                data={
                    "document_id": document_id,
                    "old_importance": result.get("old_importance"),
                    "new_importance": result.get("new_importance"),
                    "old_ttl_tier": result.get("old_ttl_tier"),
                    "new_ttl_tier": result.get("new_ttl_tier"),
                    "chunks_updated": result.get("chunks_updated", 0),
                    "collection": result.get("collection"),
                    "reason": reason,
                    "details": result.get("message")
                }
            )
        else:
            return create_tool_error(
                result.get("message", f"Failed to demote document {document_id}"),
                MCPErrorCode.RESOURCE_NOT_FOUND,
                additional_data={"document_id": document_id}
            )

    except Exception as e:
        return create_tool_error(
            f"Failed to demote document importance: {str(e)}",
            MCPErrorCode.MEMORY_SYSTEM_ERROR,
            original_error=e
        )


async def update_document_tool(
    memory_system: HierarchicalMemorySystem,
    document_id: str,
    content: str,
    metadata: Dict[str, Any] = None,
    preserve_importance: bool = True
) -> Dict[str, Any]:
    """Update a document's content in the memory system.

    This replaces the document's content while optionally preserving its
    importance score and merging metadata. Useful for correcting or
    updating stored information.

    Args:
        memory_system: HierarchicalMemorySystem instance
        document_id: The document ID to update
        content: New content for the document
        metadata: Optional metadata to merge with existing (or replace if provided)
        preserve_importance: If True, keep the original importance score

    Returns:
        Update results including old/new chunk counts
    """
    try:
        # Validate inputs
        if not document_id or not isinstance(document_id, str):
            return create_tool_error(
                "Document ID must be a non-empty string",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={"field": "document_id"}
            )

        if not content or not isinstance(content, str):
            return create_tool_error(
                "Content must be a non-empty string",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={"field": "content"}
            )

        if len(content.strip()) < 10:
            return create_tool_error(
                "Content must be at least 10 characters",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={
                    "field": "content",
                    "provided_length": len(content.strip()),
                    "minimum_length": 10
                }
            )

        # Perform the update
        result = await memory_system.update_document_content(
            document_id=document_id,
            new_content=content,
            new_metadata=metadata,
            preserve_importance=preserve_importance
        )

        if result.get("success"):
            return create_success_response(
                message=f"Document {document_id} updated successfully",
                data={
                    "document_id": document_id,
                    "new_document_id": result.get("new_document_id", document_id),
                    "old_chunks": result.get("old_chunks", 0),
                    "new_chunks": result.get("new_chunks", 0),
                    "collection": result.get("collection"),
                    "importance_preserved": result.get("importance_preserved", False),
                    "details": result.get("message")
                }
            )
        else:
            return create_tool_error(
                result.get("message", f"Failed to update document {document_id}"),
                MCPErrorCode.RESOURCE_NOT_FOUND,
                additional_data={"document_id": document_id}
            )

    except Exception as e:
        return create_tool_error(
            f"Failed to update document: {str(e)}",
            MCPErrorCode.MEMORY_SYSTEM_ERROR,
            original_error=e
        )
