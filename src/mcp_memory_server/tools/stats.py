from typing import Dict, Any


def get_memory_stats_tool(memory_system) -> dict:
    """Get comprehensive statistics about the memory system including deduplication metrics.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        
    Returns:
        Dictionary with enhanced memory system statistics
    """
    try:
        # Get base collection stats
        stats = memory_system.get_collection_stats()
        
        # Add deduplication statistics if available
        if hasattr(memory_system, 'deduplicator') and memory_system.deduplicator.enabled:
            try:
                dedup_stats = memory_system.deduplicator.get_deduplication_stats()
                stats['deduplication'] = dedup_stats
            except Exception as dedup_error:
                stats['deduplication'] = {
                    'error': str(dedup_error),
                    'message': 'Deduplication stats unavailable'
                }
        else:
            stats['deduplication'] = {
                'enabled': False,
                'message': 'Deduplication system not enabled'
            }
        
        # Add query performance statistics if available
        if hasattr(memory_system, 'query_monitor'):
            try:
                query_stats = memory_system.get_query_performance_stats('day')
                stats['query_performance'] = query_stats
            except Exception as query_error:
                stats['query_performance'] = {
                    'error': str(query_error),
                    'message': 'Query performance stats unavailable'
                }
        
        # Add enhanced system metrics
        stats['enhanced_metrics'] = _calculate_enhanced_metrics(stats)
        
        # Return MCP-compliant format
        return {
            "total_documents": stats.get('enhanced_metrics', {}).get('total_documents', 0),
            "collections": stats.get('collections', {})
        }
    except Exception as e:
        raise Exception(f"Failed to get memory stats: {str(e)}")


def _calculate_enhanced_metrics(stats: dict) -> dict:
    """Calculate enhanced system metrics from base statistics."""
    enhanced = {
        'total_documents': 0,
        'storage_efficiency': 0.0,
        'deduplication_impact': 0.0,
        'query_performance_score': 0.0,
        'system_optimization_score': 0.0
    }
    
    try:
        # Calculate total documents across collections
        collections = stats.get('collections', {})
        enhanced['total_documents'] = sum(
            c.get('count', 0) for c in collections.values() 
            if isinstance(c, dict)
        )
        
        # Calculate deduplication impact
        dedup_stats = stats.get('deduplication', {})
        if dedup_stats.get('enabled', False):
            enhanced['deduplication_impact'] = dedup_stats.get('deduplication_efficiency', 0) / 100.0
            
            # Storage efficiency based on deduplication
            documents_saved = dedup_stats.get('total_documents_merged', 0)
            if enhanced['total_documents'] > 0:
                enhanced['storage_efficiency'] = min(
                    (documents_saved / enhanced['total_documents']) * 100, 100
                )
        
        # Query performance score
        query_stats = stats.get('query_performance', {})
        if 'mean_quality' in query_stats.get('quality_metrics', {}):
            enhanced['query_performance_score'] = query_stats['quality_metrics']['mean_quality']
        
        # Overall system optimization score
        optimization_factors = [
            enhanced['storage_efficiency'] / 100.0,
            enhanced['deduplication_impact'],
            enhanced['query_performance_score']
        ]
        
        valid_factors = [f for f in optimization_factors if f > 0]
        if valid_factors:
            enhanced['system_optimization_score'] = sum(valid_factors) / len(valid_factors)
        
    except Exception as e:
        enhanced['calculation_error'] = str(e)
    
    return enhanced


def get_system_health_tool(memory_system, config) -> dict:
    """Get comprehensive system health information with deduplication and performance metrics.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        config: Configuration object
        
    Returns:
        Dictionary with enhanced system health metrics
    """
    try:
        # Get collection stats
        collection_stats = memory_system.get_collection_stats()
        
        # Get configuration health
        config_health = {
            "database_config": bool(config.get_database_config()),
            "embeddings_config": bool(config.get_embeddings_config()),
            "memory_scoring_config": bool(config.get_memory_scoring_config()),
            "server_config": bool(config.get_server_config()),
            "deduplication_config": bool(config.get_deduplication_config().get('enabled', False))
        }
        
        # Calculate base collection health
        total_collections = len(collection_stats.get("collections", {}))
        active_collections = sum(1 for c in collection_stats.get("collections", {}).values() 
                               if c.get("status") == "active")
        
        collection_health = (active_collections / total_collections) if total_collections > 0 else 0
        
        # Enhanced health scoring with deduplication and performance factors
        health_factors = [collection_health]
        
        # Deduplication health
        if hasattr(memory_system, 'deduplicator') and memory_system.deduplicator.enabled:
            try:
                dedup_stats = memory_system.deduplicator.get_deduplication_stats()
                dedup_efficiency = dedup_stats.get('deduplication_efficiency', 0) / 100.0
                health_factors.append(min(dedup_efficiency + 0.5, 1.0))  # Base + efficiency bonus
            except:
                health_factors.append(0.7)  # Dedup enabled but stats unavailable
        else:
            health_factors.append(0.6)  # No deduplication
        
        # Query performance health
        if hasattr(memory_system, 'query_monitor'):
            try:
                query_stats = memory_system.get_query_performance_stats('hour')
                if query_stats.get('query_count', 0) > 0:
                    perf_health = query_stats.get('quality_metrics', {}).get('mean_quality', 0.5)
                    response_health = 1.0 - min(
                        query_stats.get('response_time_stats', {}).get('mean_ms', 100) / 1000.0, 
                        1.0
                    )
                    query_health = (perf_health + response_health) / 2
                    health_factors.append(query_health)
                else:
                    health_factors.append(0.7)  # No recent queries
            except:
                health_factors.append(0.6)  # Query monitoring unavailable
        else:
            health_factors.append(0.5)  # No query monitoring
        
        # Calculate weighted health score
        overall_health_score = sum(health_factors) / len(health_factors)
        
        # System optimization metrics
        optimization_status = _assess_system_optimization(memory_system)
        
        # Determine status with enhanced criteria
        if overall_health_score > 0.8:
            status = "optimal"
        elif overall_health_score > 0.7:
            status = "healthy" 
        elif overall_health_score > 0.5:
            status = "degraded"
        else:
            status = "critical"
        
        return {
            "success": True,
            "health_score": overall_health_score,
            "status": status,
            "collection_stats": collection_stats,
            "config_health": config_health,
            "health_breakdown": {
                "collection_health": collection_health,
                "deduplication_health": health_factors[1] if len(health_factors) > 1 else None,
                "query_performance_health": health_factors[2] if len(health_factors) > 2 else None
            },
            "optimization_status": optimization_status,
            "recommendations": _generate_health_recommendations(overall_health_score, optimization_status)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "health_score": 0,
            "status": "critical",
            "message": "Failed to assess system health"
        }


def _assess_system_optimization(memory_system) -> dict:
    """Assess system optimization status."""
    optimization = {
        'deduplication_active': False,
        'query_monitoring_active': False,
        'progressive_cleanup_active': False,
        'smart_routing_active': False,
        'optimization_score': 0.0
    }
    
    try:
        # Check deduplication
        if hasattr(memory_system, 'deduplicator') and memory_system.deduplicator.enabled:
            optimization['deduplication_active'] = True
        
        # Check query monitoring
        if hasattr(memory_system, 'query_monitor'):
            optimization['query_monitoring_active'] = True
        
        # Check for recent query optimizations (if query history exists)
        if hasattr(memory_system, 'query_monitor') and memory_system.query_monitor.query_history:
            recent_queries = list(memory_system.query_monitor.query_history)[-10:]
            if any(q.get('smart_routing_used', False) for q in recent_queries):
                optimization['smart_routing_active'] = True
        
        # Calculate optimization score
        active_features = sum([
            optimization['deduplication_active'],
            optimization['query_monitoring_active'],
            optimization['smart_routing_active']
        ])
        optimization['optimization_score'] = active_features / 3.0
        
    except Exception as e:
        optimization['error'] = str(e)
    
    return optimization


def _generate_health_recommendations(health_score: float, optimization_status: dict) -> list:
    """Generate health improvement recommendations."""
    recommendations = []
    
    if health_score < 0.7:
        recommendations.append({
            'priority': 'high',
            'type': 'performance',
            'message': 'System health is below optimal. Consider running maintenance tasks.'
        })
    
    if not optimization_status.get('deduplication_active', False):
        recommendations.append({
            'priority': 'medium',
            'type': 'optimization',
            'message': 'Enable deduplication to improve storage efficiency and query performance.'
        })
    
    if not optimization_status.get('query_monitoring_active', False):
        recommendations.append({
            'priority': 'low',
            'type': 'monitoring',
            'message': 'Enable query monitoring for better performance insights.'
        })
    
    if optimization_status.get('optimization_score', 0) < 0.5:
        recommendations.append({
            'priority': 'medium',
            'type': 'features',
            'message': 'Consider enabling more optimization features for better performance.'
        })
    
    if health_score > 0.8 and not recommendations:
        recommendations.append({
            'priority': 'info',
            'type': 'status',
            'message': 'System is operating optimally. No immediate actions required.'
        })
    
    return recommendations