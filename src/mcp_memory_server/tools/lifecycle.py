from typing import Dict, Any, Optional
from ..memory.lifecycle import LifecycleManager
from ..server.errors import create_success_response, create_tool_error, MCPErrorCode


def get_lifecycle_stats_tool(lifecycle_manager: LifecycleManager) -> Dict[str, Any]:
    """Get comprehensive lifecycle management statistics.

    Args:
        lifecycle_manager: LifecycleManager instance

    Returns:
        Lifecycle statistics and health information
    """
    try:
        stats = lifecycle_manager.get_lifecycle_stats()

        # Return MCP-compliant format
        return create_success_response(
            message="Lifecycle statistics retrieved successfully",
            data={
                "ttl_manager": stats.get('ttl_manager', {}),
                "maintenance": stats.get('maintenance', {})
            }
        )

    except Exception as e:
        return create_tool_error(
            f"Failed to get lifecycle stats: {str(e)}",
            MCPErrorCode.LIFECYCLE_ERROR,
            original_error=e
        )


async def cleanup_expired_memories_tool(lifecycle_manager: LifecycleManager,
                                        collection: Optional[str] = None) -> Dict[str, Any]:
    """Clean up expired memories based on TTL.

    Args:
        lifecycle_manager: LifecycleManager instance
        collection: Specific collection to clean (optional)

    Returns:
        Cleanup results and statistics
    """
    try:
        results = await lifecycle_manager.cleanup_expired_documents(collection)

        return create_success_response(
            message=f"Cleanup completed for {collection or 'all collections'}",
            data={"cleanup_results": results}
        )

    except Exception as e:
        return create_tool_error(
            f"Failed to cleanup expired memories: {str(e)}",
            MCPErrorCode.LIFECYCLE_ERROR,
            original_error=e
        )


async def refresh_memory_aging_tool(lifecycle_manager: LifecycleManager,
                                    collection: Optional[str] = None, sample_size: int = 100) -> Dict[str, Any]:
    """Refresh aging scores for memories that need updating.

    Args:
        lifecycle_manager: LifecycleManager instance
        collection: Specific collection to refresh (optional)
        sample_size: Number of documents to process per collection

    Returns:
        Refresh results and statistics
    """
    try:
        results = await lifecycle_manager.refresh_aging_scores(collection, sample_size)

        return create_success_response(
            message=f"Aging refresh completed for {collection or 'all collections'}",
            data={"refresh_results": results}
        )

    except Exception as e:
        return create_tool_error(
            f"Failed to refresh memory aging: {str(e)}",
            MCPErrorCode.LIFECYCLE_ERROR,
            original_error=e
        )


def start_background_maintenance_tool(lifecycle_manager: LifecycleManager) -> Dict[str, Any]:
    """Start background maintenance processes.

    Args:
        lifecycle_manager: LifecycleManager instance

    Returns:
        Operation result
    """
    try:
        lifecycle_manager.start_background_maintenance()

        return create_success_response(
            message="Background maintenance started successfully",
            data={
                "message": "Background maintenance started successfully",
                "maintenance_enabled": lifecycle_manager.maintenance_enabled
            }
        )

    except Exception as e:
        return create_tool_error(
            f"Failed to start background maintenance: {str(e)}",
            MCPErrorCode.LIFECYCLE_ERROR,
            original_error=e
        )


def stop_background_maintenance_tool(lifecycle_manager: LifecycleManager) -> Dict[str, Any]:
    """Stop background maintenance processes.

    Args:
        lifecycle_manager: LifecycleManager instance

    Returns:
        Operation result
    """
    try:
        lifecycle_manager.stop_background_maintenance()

        return create_success_response(
            message="Background maintenance stopped successfully",
            data={
                "message": "Background maintenance stopped successfully"
            }
        )

    except Exception as e:
        return create_tool_error(
            f"Failed to stop background maintenance: {str(e)}",
            MCPErrorCode.LIFECYCLE_ERROR,
            original_error=e
        )
