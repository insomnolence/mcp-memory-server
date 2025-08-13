from typing import Dict, Any
from ..memory.lifecycle import LifecycleManager


def get_lifecycle_stats_tool(lifecycle_manager: LifecycleManager) -> Dict[str, Any]:
    """Get comprehensive lifecycle management statistics.
    
    Args:
        lifecycle_manager: LifecycleManager instance
        
    Returns:
        Lifecycle statistics and health information
    """
    try:
        stats = lifecycle_manager.get_lifecycle_stats()
        
        return {
            "success": True,
            "lifecycle_stats": stats
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def cleanup_expired_memories_tool(lifecycle_manager: LifecycleManager, 
                                collection: str = None) -> Dict[str, Any]:
    """Clean up expired memories based on TTL.
    
    Args:
        lifecycle_manager: LifecycleManager instance
        collection: Specific collection to clean (optional)
        
    Returns:
        Cleanup results and statistics
    """
    try:
        results = lifecycle_manager.cleanup_expired_documents(collection)
        
        return {
            "success": True,
            "cleanup_results": results
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def refresh_memory_aging_tool(lifecycle_manager: LifecycleManager,
                            collection: str = None, sample_size: int = 100) -> Dict[str, Any]:
    """Refresh aging scores for memories that need updating.
    
    Args:
        lifecycle_manager: LifecycleManager instance
        collection: Specific collection to refresh (optional)
        sample_size: Number of documents to process per collection
        
    Returns:
        Refresh results and statistics
    """
    try:
        results = lifecycle_manager.refresh_aging_scores(collection, sample_size)
        
        return {
            "success": True,
            "refresh_results": results
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def start_background_maintenance_tool(lifecycle_manager: LifecycleManager) -> Dict[str, Any]:
    """Start background maintenance processes.
    
    Args:
        lifecycle_manager: LifecycleManager instance
        
    Returns:
        Operation result
    """
    try:
        lifecycle_manager.start_background_maintenance()
        
        return {
            "success": True,
            "message": "Background maintenance started",
            "maintenance_enabled": lifecycle_manager.maintenance_enabled
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def stop_background_maintenance_tool(lifecycle_manager: LifecycleManager) -> Dict[str, Any]:
    """Stop background maintenance processes.
    
    Args:
        lifecycle_manager: LifecycleManager instance
        
    Returns:
        Operation result
    """
    try:
        lifecycle_manager.stop_background_maintenance()
        
        return {
            "success": True,
            "message": "Background maintenance stopped"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}