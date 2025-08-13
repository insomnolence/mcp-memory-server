from typing import Dict, Any


def get_memory_stats_tool(memory_system) -> dict:
    """Get statistics about the memory system.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        
    Returns:
        Dictionary with memory system statistics
    """
    try:
        stats = memory_system.get_collection_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise Exception(f"Failed to get memory stats: {str(e)}")


def get_system_health_tool(memory_system, config) -> dict:
    """Get comprehensive system health information.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        config: Configuration object
        
    Returns:
        Dictionary with system health metrics
    """
    try:
        # Get collection stats
        collection_stats = memory_system.get_collection_stats()
        
        # Get configuration health
        config_health = {
            "database_config": bool(config.get_database_config()),
            "embeddings_config": bool(config.get_embeddings_config()),
            "memory_scoring_config": bool(config.get_memory_scoring_config()),
            "server_config": bool(config.get_server_config())
        }
        
        # Calculate overall health score
        total_collections = len(collection_stats.get("collections", {}))
        active_collections = sum(1 for c in collection_stats.get("collections", {}).values() 
                               if c.get("status") == "active")
        
        health_score = (active_collections / total_collections) if total_collections > 0 else 0
        
        return {
            "success": True,
            "health_score": health_score,
            "collection_stats": collection_stats,
            "config_health": config_health,
            "status": "healthy" if health_score > 0.75 else "degraded" if health_score > 0.5 else "critical"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "health_score": 0,
            "status": "critical"
        }