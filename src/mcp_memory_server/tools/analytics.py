"""
Analytics Tools for MCP Server

Provides tools for accessing comprehensive system analytics, intelligence insights,
predictive analytics, and optimization recommendations.
"""

import logging
from typing import Dict, Any


def get_comprehensive_analytics_tool(memory_system) -> dict:
    """Get comprehensive system analytics with intelligence insights.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        
    Returns:
        Dictionary with comprehensive analytics and intelligence insights
    """
    try:
        analytics = memory_system.get_comprehensive_analytics()
        
        if 'error' in analytics:
            return {
                "success": False,
                "message": analytics.get('message', 'Analytics system not available'),
                "error": analytics.get('error')
            }
        
        # Ensure MCP-compliant format with required fields
        if 'overall_health' not in analytics:
            # Calculate overall health from available data
            analytics['overall_health'] = _calculate_overall_health(analytics)
        
        # Return MCP-compliant format
        return {
            "analytics": analytics,
            "message": "Comprehensive analytics generated successfully"
        }
        
    except Exception as e:
        logging.error(f"Failed to get comprehensive analytics: {e}")
        return {
            "success": False,
            "message": f"Failed to get comprehensive analytics: {str(e)}",
            "error": str(e)
        }


def get_system_intelligence_tool(memory_system, focus_area: str = "all") -> dict:
    """Get system intelligence insights for a specific focus area.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        focus_area: Focus area ('storage', 'performance', 'deduplication', 'all')
        
    Returns:
        Dictionary with intelligence insights for the specified area
    """
    try:
        # Get comprehensive analytics
        full_analytics = memory_system.get_comprehensive_analytics()
        
        if 'error' in full_analytics:
            return {
                "success": False,
                "message": "Intelligence system not available",
                "focus_area": focus_area
            }
        
        # Extract relevant sections based on focus area
        if focus_area == "storage":
            focused_insights = {
                'system_overview': full_analytics.get('system_overview', {}),
                'storage_analytics': full_analytics.get('storage_analytics', {}),
                'optimization_recommendations': [
                    rec for rec in full_analytics.get('optimization_recommendations', [])
                    if rec.get('category') == 'storage'
                ]
            }
        elif focus_area == "performance":
            focused_insights = {
                'query_performance_insights': full_analytics.get('query_performance_insights', {}),
                'performance_trends': full_analytics.get('trend_analysis', {}).get('performance_trends', {}),
                'optimization_recommendations': [
                    rec for rec in full_analytics.get('optimization_recommendations', [])
                    if rec.get('category') == 'performance'
                ]
            }
        elif focus_area == "deduplication":
            focused_insights = {
                'deduplication_intelligence': full_analytics.get('deduplication_intelligence', {}),
                'cost_benefit_analysis': full_analytics.get('cost_benefit_analysis', {}),
                'optimization_recommendations': [
                    rec for rec in full_analytics.get('optimization_recommendations', [])
                    if rec.get('category') in ['optimization', 'storage']
                ]
            }
        else:  # focus_area == "all"
            focused_insights = full_analytics
        
        # Return MCP-compliant format
        return {
            "intelligence": focused_insights,
            "focus_area": focus_area,
            "message": f"Intelligence insights generated for {focus_area} area"
        }
        
    except Exception as e:
        logging.error(f"Failed to get system intelligence: {e}")
        return {
            "success": False,
            "message": f"Failed to get system intelligence: {str(e)}",
            "error": str(e)
        }


def get_optimization_recommendations_tool(memory_system, priority_filter: str = "all") -> dict:
    """Get intelligent optimization recommendations.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        priority_filter: Priority filter ('high', 'medium', 'low', 'all')
        
    Returns:
        Dictionary with optimization recommendations
    """
    try:
        # Get comprehensive analytics to extract recommendations
        analytics = memory_system.get_comprehensive_analytics()
        
        if 'error' in analytics:
            return {
                "success": False,
                "message": "Cannot generate recommendations - analytics system not available"
            }
        
        all_recommendations = analytics.get('optimization_recommendations', [])
        
        # Filter recommendations by priority if specified
        if priority_filter != "all":
            filtered_recommendations = [
                rec for rec in all_recommendations
                if rec.get('priority') == priority_filter
            ]
        else:
            filtered_recommendations = all_recommendations
        
        # Add summary statistics
        priority_counts = {}
        category_counts = {}
        
        for rec in all_recommendations:
            priority = rec.get('priority', 'unknown')
            category = rec.get('category', 'unknown')
            
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Calculate potential impact
        total_roi = sum(rec.get('roi_score', 0) for rec in filtered_recommendations)
        avg_roi = total_roi / len(filtered_recommendations) if filtered_recommendations else 0
        
        return {
            "success": True,
            "priority_filter": priority_filter,
            "recommendations": filtered_recommendations,
            "summary": {
                "total_recommendations": len(all_recommendations),
                "filtered_recommendations": len(filtered_recommendations),
                "priority_distribution": priority_counts,
                "category_distribution": category_counts,
                "average_roi_score": round(avg_roi, 2),
                "high_impact_count": len([r for r in filtered_recommendations if r.get('roi_score', 0) > 8])
            },
            "message": f"Retrieved {len(filtered_recommendations)} optimization recommendations"
        }
        
    except Exception as e:
        logging.error(f"Failed to get optimization recommendations: {e}")
        return {
            "success": False,
            "message": f"Failed to get optimization recommendations: {str(e)}",
            "error": str(e)
        }


def get_predictive_insights_tool(memory_system, prediction_type: str = "all") -> dict:
    """Get predictive analytics insights.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        prediction_type: Type of prediction ('storage', 'performance', 'resources', 'all')
        
    Returns:
        Dictionary with predictive insights
    """
    try:
        # Get comprehensive analytics to extract predictive insights
        analytics = memory_system.get_comprehensive_analytics()
        
        if 'error' in analytics:
            return {
                "success": False,
                "message": "Predictive analytics not available - analytics system not available"
            }
        
        predictive_analytics = analytics.get('predictive_analytics', {})
        
        if not predictive_analytics.get('enabled', False):
            return {
                "success": False,
                "message": "Predictive analytics is not enabled in the system configuration"
            }
        
        # Extract specific prediction types
        if prediction_type == "storage":
            focused_predictions = {
                'storage_growth': predictive_analytics.get('storage_growth', {}),
                'prediction_horizon': predictive_analytics.get('prediction_horizon_days', 7)
            }
        elif prediction_type == "performance":
            focused_predictions = {
                'query_performance': predictive_analytics.get('query_performance', {}),
                'prediction_horizon': predictive_analytics.get('prediction_horizon_days', 7)
            }
        elif prediction_type == "resources":
            focused_predictions = {
                'resource_requirements': predictive_analytics.get('resource_requirements', {}),
                'prediction_horizon': predictive_analytics.get('prediction_horizon_days', 7)
            }
        else:  # prediction_type == "all"
            focused_predictions = predictive_analytics
        
        # Return MCP-compliant format
        return {
            "insights": focused_predictions,
            "prediction_type": prediction_type,
            "confidence_scores": predictive_analytics.get('confidence_scores', {}),
            "recommended_actions": predictive_analytics.get('recommended_actions', []),
            "message": f"Predictive insights generated for {prediction_type}"
        }
        
    except Exception as e:
        logging.error(f"Failed to get predictive insights: {e}")
        return {
            "success": False,
            "message": f"Failed to get predictive insights: {str(e)}",
            "error": str(e)
        }


def get_chunk_relationships_tool(memory_system, document_id: str = None) -> dict:
    """Get chunk relationship statistics and analysis.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem  
        document_id: Optional document ID to get specific relationship info
        
    Returns:
        Dictionary with chunk relationship information
    """
    try:
        if not hasattr(memory_system, 'chunk_manager'):
            return {
                "success": False,
                "message": "Chunk relationship tracking is not enabled in this system"
            }
        
        if document_id:
            # Get specific document context
            document_context = memory_system.chunk_manager.get_document_context(document_id)
            
            if 'error' in document_context:
                return {
                    "success": False,
                    "message": f"Document {document_id} not found in relationship tracking",
                    "document_id": document_id
                }
            
            return {
                "success": True,
                "document_id": document_id,
                "document_context": document_context,
                "message": f"Retrieved relationship context for document {document_id}"
            }
        else:
            # Get overall relationship statistics
            relationship_stats = memory_system.get_chunk_relationship_stats()
            
            if 'error' in relationship_stats:
                return {
                    "success": False,
                    "message": relationship_stats.get('message', 'Chunk relationship stats not available'),
                    "error": relationship_stats.get('error')
                }
            
            # Return MCP-compliant format
            return {
                "relationships": relationship_stats,
                "message": "Retrieved comprehensive chunk relationship statistics"
            }
        
    except Exception as e:
        logging.error(f"Failed to get chunk relationships: {e}")
        return {
            "success": False,
            "message": f"Failed to get chunk relationships: {str(e)}",
            "error": str(e)
        }


def get_system_health_assessment_tool(memory_system) -> dict:
    """Get comprehensive system health assessment with intelligence insights.
    
    Args:
        memory_system: Instance of HierarchicalMemorySystem
        
    Returns:
        Dictionary with comprehensive health assessment
    """
    try:
        # Get comprehensive analytics to extract health assessment
        analytics = memory_system.get_comprehensive_analytics()
        
        if 'error' in analytics:
            return {
                "success": False,
                "message": "Health assessment not available - analytics system not available"
            }
        
        health_assessment = analytics.get('system_health_assessment', {})
        
        # Also get basic system health for comparison
        basic_health = {}
        try:
            from ..stats import get_system_health_tool
            # This would require config, so we'll create a simplified version
            collection_stats = memory_system.get_collection_stats()
            basic_health = {
                'collections_active': len([
                    c for c in collection_stats.get('collections', {}).values()
                    if isinstance(c, dict) and c.get('status') == 'active'
                ]),
                'total_documents': sum(
                    c.get('count', 0) for c in collection_stats.get('collections', {}).values()
                    if isinstance(c, dict)
                )
            }
        except Exception:
            basic_health = {}
        
        # Combine assessments
        comprehensive_health = {
            'health_status': health_assessment.get('status', 'good'),  # Add expected field
            'intelligent_assessment': health_assessment,
            'basic_metrics': basic_health,
            'system_overview': analytics.get('system_overview', {}),
            'critical_recommendations': [
                rec for rec in analytics.get('optimization_recommendations', [])
                if rec.get('priority') == 'high'
            ]
        }
        
        return {
            "success": True,
            "health_assessment": comprehensive_health,
            "overall_status": health_assessment.get('status', 'unknown'),
            "health_score": health_assessment.get('overall_score', 0),
            "message": "Comprehensive health assessment completed"
        }
        
    except Exception as e:
        logging.error(f"Failed to get system health assessment: {e}")
        return {
            "success": False,
            "message": f"Failed to get system health assessment: {str(e)}",
            "error": str(e)
        }


def _calculate_overall_health(analytics: dict) -> dict:
    """Calculate overall system health from analytics data."""
    health = {
        "score": 0.7,  # Default decent health
        "status": "good",
        "factors": {}
    }
    
    try:
        # Factor in performance metrics if available
        performance_data = analytics.get('performance_analysis', {})
        if 'query_performance_score' in performance_data:
            perf_score = performance_data['query_performance_score']
            health["factors"]["query_performance"] = perf_score
            health["score"] = (health["score"] + perf_score) / 2
        
        # Factor in storage optimization
        storage_data = analytics.get('storage_analysis', {})
        if 'storage_efficiency' in storage_data:
            storage_score = storage_data['storage_efficiency'] / 100.0
            health["factors"]["storage_efficiency"] = storage_score
            health["score"] = (health["score"] + storage_score) / 2
        
        # Factor in deduplication effectiveness
        dedup_data = analytics.get('deduplication_intelligence', {})
        if dedup_data.get('enabled', False):
            dedup_score = 0.8  # Good if enabled
            health["factors"]["deduplication"] = dedup_score
            health["score"] = (health["score"] + dedup_score) / 2
        else:
            health["factors"]["deduplication"] = 0.5  # Neutral if disabled
            health["score"] = (health["score"] + 0.5) / 2
        
        # Set status based on score
        if health["score"] >= 0.8:
            health["status"] = "excellent"
        elif health["score"] >= 0.7:
            health["status"] = "good"
        elif health["score"] >= 0.5:
            health["status"] = "fair"
        else:
            health["status"] = "poor"
            
    except Exception as e:
        health["error"] = str(e)
    
    return health