"""
Performance Monitoring Tools for MCP Server

Provides tools for accessing query performance metrics and real-time monitoring data.
"""

import logging
from typing import Dict, Any


def get_query_performance_tool(memory_system, time_window: str = "day") -> dict:
    """Get query performance statistics for the specified time window.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        time_window: Time window for statistics ('hour', 'day', 'week', 'all')
        
    Returns:
        Dictionary with query performance statistics
    """
    try:
        # Validate time window
        valid_windows = ['hour', 'day', 'week', 'all']
        if time_window not in valid_windows:
            return {
                "success": False,
                "message": f"Invalid time window. Must be one of: {', '.join(valid_windows)}",
                "time_window": time_window
            }
        
        # Get performance statistics
        if hasattr(memory_system, 'query_monitor'):
            stats = memory_system.get_query_performance_stats(time_window)
            
            # Add interpretation and insights
            insights = _interpret_performance_stats(stats)
            
            return {
                "success": True,
                "time_window": time_window,
                "performance_stats": stats,
                "insights": insights,
                "message": f"Retrieved query performance statistics for {time_window} window"
            }
        else:
            return {
                "success": False,
                "message": "Query monitoring not enabled on this system",
                "recommendation": "Enable query monitoring in configuration to access performance statistics"
            }
            
    except Exception as e:
        logging.error(f"Failed to get query performance statistics: {e}")
        return {
            "success": False,
            "message": f"Failed to get query performance statistics: {str(e)}",
            "error": str(e)
        }


def get_real_time_metrics_tool(memory_system) -> dict:
    """Get real-time performance metrics and system status.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        
    Returns:
        Dictionary with real-time metrics
    """
    try:
        if hasattr(memory_system, 'query_monitor'):
            metrics = memory_system.query_monitor.get_real_time_metrics()
            
            # Add system status indicators
            status_indicators = _calculate_status_indicators(metrics)
            
            return {
                "success": True,
                "real_time_metrics": metrics,
                "status_indicators": status_indicators,
                "message": "Real-time metrics retrieved successfully"
            }
        else:
            return {
                "success": False,
                "message": "Query monitoring not enabled on this system",
                "recommendation": "Enable query monitoring in configuration for real-time metrics"
            }
            
    except Exception as e:
        logging.error(f"Failed to get real-time metrics: {e}")
        return {
            "success": False,
            "message": f"Failed to get real-time metrics: {str(e)}",
            "error": str(e)
        }


def export_performance_data_tool(memory_system, format: str = "json", 
                                time_window: str = "all") -> dict:
    """Export performance data in the specified format.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        format: Export format ('json', 'dict', 'csv')
        time_window: Time window for export ('hour', 'day', 'week', 'all')
        
    Returns:
        Dictionary with exported performance data
    """
    try:
        # Validate parameters
        valid_formats = ['json', 'dict', 'csv']
        valid_windows = ['hour', 'day', 'week', 'all']
        
        if format not in valid_formats:
            return {
                "success": False,
                "message": f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            }
        
        if time_window not in valid_windows:
            return {
                "success": False,
                "message": f"Invalid time window. Must be one of: {', '.join(valid_windows)}"
            }
        
        if hasattr(memory_system, 'query_monitor'):
            # Get performance summary for the time window
            summary = memory_system.query_monitor.get_performance_summary(time_window)
            
            # Export in requested format
            exported_data = memory_system.query_monitor.export_metrics(format)
            
            return {
                "success": True,
                "format": format,
                "time_window": time_window,
                "summary": summary,
                "exported_data": exported_data if format == 'dict' else None,
                "data_size": len(str(exported_data)),
                "message": f"Performance data exported in {format} format for {time_window} window"
            }
        else:
            return {
                "success": False,
                "message": "Query monitoring not enabled on this system"
            }
            
    except Exception as e:
        logging.error(f"Failed to export performance data: {e}")
        return {
            "success": False,
            "message": f"Failed to export performance data: {str(e)}",
            "error": str(e)
        }


def _interpret_performance_stats(stats: dict) -> dict:
    """Interpret performance statistics and provide insights."""
    insights = {
        "performance_grade": "unknown",
        "key_metrics": {},
        "recommendations": [],
        "trends": {}
    }
    
    try:
        query_count = stats.get('query_count', 0)
        if query_count == 0:
            insights["performance_grade"] = "no_data"
            insights["recommendations"].append("No queries to analyze. System needs usage to generate insights.")
            return insights
        
        # Response time analysis
        response_stats = stats.get('response_time_stats', {})
        mean_response = response_stats.get('mean_ms', 0)
        p95_response = response_stats.get('p95_ms', 0)
        
        insights["key_metrics"]["average_response_time"] = f"{mean_response:.1f}ms"
        insights["key_metrics"]["p95_response_time"] = f"{p95_response:.1f}ms"
        
        # Performance grading
        if mean_response < 100:
            insights["performance_grade"] = "excellent"
        elif mean_response < 300:
            insights["performance_grade"] = "good"
        elif mean_response < 500:
            insights["performance_grade"] = "fair"
        else:
            insights["performance_grade"] = "poor"
            insights["recommendations"].append("Average response time is high. Consider enabling optimizations.")
        
        # Query quality analysis
        quality_metrics = stats.get('quality_metrics', {})
        mean_quality = quality_metrics.get('mean_quality', 0)
        insights["key_metrics"]["average_quality"] = f"{mean_quality:.2f}"
        
        if mean_quality < 0.6:
            insights["recommendations"].append("Query result quality is below optimal. Review query patterns.")
        
        # Deduplication impact analysis
        dedup_impact = stats.get('deduplication_impact', {})
        hit_rate = dedup_impact.get('mean_hit_rate', 0)
        insights["key_metrics"]["deduplication_hit_rate"] = f"{hit_rate:.1%}"
        
        if hit_rate > 0.2:
            insights["recommendations"].append("High deduplication hit rate indicates good storage optimization.")
        elif hit_rate < 0.05:
            insights["recommendations"].append("Low deduplication hit rate. Consider reviewing duplicate detection thresholds.")
        
        # Performance distribution
        perf_dist = stats.get('performance_distribution', {})
        fast_percentage = perf_dist.get('fast_percentage', 0)
        insights["key_metrics"]["fast_queries_percentage"] = f"{fast_percentage:.1f}%"
        
        if fast_percentage > 80:
            insights["trends"]["response_time"] = "excellent"
        elif fast_percentage > 60:
            insights["trends"]["response_time"] = "good"
        else:
            insights["trends"]["response_time"] = "needs_improvement"
            insights["recommendations"].append("Consider optimizing slow queries or enabling smart routing.")
        
        # Optimization usage
        opt_usage = stats.get('optimization_usage', {})
        smart_routing_usage = opt_usage.get('smart_routing_usage', 0)
        
        if smart_routing_usage < 50:
            insights["recommendations"].append("Smart routing is underutilized. Enable for better performance.")
        
    except Exception as e:
        insights["error"] = f"Failed to interpret statistics: {str(e)}"
    
    return insights


def _calculate_status_indicators(metrics: dict) -> dict:
    """Calculate system status indicators from real-time metrics."""
    indicators = {
        "system_load": "normal",
        "response_health": "good",
        "query_activity": "normal",
        "overall_status": "healthy"
    }
    
    try:
        # Query activity indicator
        queries_per_minute = metrics.get('queries_per_minute', 0)
        if queries_per_minute > 10:
            indicators["query_activity"] = "high"
        elif queries_per_minute > 3:
            indicators["query_activity"] = "normal"
        elif queries_per_minute > 0:
            indicators["query_activity"] = "low"
        else:
            indicators["query_activity"] = "idle"
        
        # Response health indicator
        avg_response = metrics.get('recent_average_response_ms', 0)
        if avg_response < 200:
            indicators["response_health"] = "excellent"
        elif avg_response < 500:
            indicators["response_health"] = "good"
        elif avg_response < 1000:
            indicators["response_health"] = "fair"
        else:
            indicators["response_health"] = "poor"
        
        # System health indicator
        system_health = metrics.get('system_health_score', 0.5)
        if system_health > 0.8:
            indicators["overall_status"] = "optimal"
        elif system_health > 0.6:
            indicators["overall_status"] = "healthy"
        elif system_health > 0.4:
            indicators["overall_status"] = "degraded"
        else:
            indicators["overall_status"] = "critical"
        
        # System load (based on response times and activity)
        load_score = min(avg_response / 1000.0 + queries_per_minute / 20.0, 2.0)
        if load_score < 0.5:
            indicators["system_load"] = "light"
        elif load_score < 1.0:
            indicators["system_load"] = "normal"
        elif load_score < 1.5:
            indicators["system_load"] = "high"
        else:
            indicators["system_load"] = "very_high"
    
    except Exception as e:
        indicators["error"] = f"Failed to calculate indicators: {str(e)}"
    
    return indicators