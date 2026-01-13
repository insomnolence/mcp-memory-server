"""
Analytics and Intelligence System (Simplified)

Provides practical analytics for memory system monitoring:
- System overview and health
- Storage patterns and distribution
- Deduplication effectiveness
- Query performance metrics
- Actionable optimization recommendations

Note: Predictive analytics and cost-benefit analysis features have been removed
as they were over-engineered for this use case.
"""

import time
import logging
import statistics
from typing import Dict, Any, List, Optional


class MemoryIntelligenceSystem:
    """Analytics system for memory optimization monitoring."""

    def __init__(self, memory_system: Any, analytics_config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the intelligence system.

        Args:
            memory_system: Reference to HierarchicalMemorySystem
            analytics_config: Configuration for analytics behavior
        """
        self.memory_system = memory_system
        self.config = analytics_config or self._get_default_config()

        # Analytics tracking
        self.analytics_history: List[Dict[str, Any]] = []
        self.optimization_recommendations: List[Dict[str, Any]] = []

        # Start time for uptime tracking
        self.system_start_time = time.time()

    def _get_default_config(self) -> dict:
        """Default configuration for analytics system."""
        return {
            'history_retention_days': 30,
            'cache_duration_minutes': 15,
        }

    def generate_comprehensive_analytics(self) -> Dict[str, Any]:
        """Generate comprehensive system analytics.

        Returns practical metrics for monitoring and optimization.
        """
        current_time = time.time()

        analytics = {
            'timestamp': current_time,
            'system_overview': self._generate_system_overview(),
            'storage_analytics': self._analyze_storage_patterns(),
            'deduplication_intelligence': self._analyze_deduplication_effectiveness(),
            'query_performance_insights': self._analyze_query_patterns(),
            'optimization_recommendations': self._generate_optimization_recommendations(),
            'system_health_assessment': self._assess_system_health(),
            # Removed features - return status instead of fake data
            'predictive_analytics': {'enabled': False, 'status': 'not_implemented'},
            'trend_analysis': {'status': 'not_implemented'},
            'cost_benefit_analysis': {'status': 'not_implemented'},
        }

        # Store analytics in history
        system_overview = analytics.get('system_overview', {})
        health_assessment = analytics.get('system_health_assessment', {})
        self.analytics_history.append({
            'timestamp': current_time,
            'total_documents': system_overview.get('total_documents', 0) if isinstance(system_overview, dict) else 0,
            'health_score': health_assessment.get('overall_score', 0) if isinstance(health_assessment, dict) else 0,
        })

        # Cleanup old history
        self._cleanup_analytics_history()

        return analytics

    def _generate_system_overview(self) -> Dict[str, Any]:
        """Generate high-level system overview with real metrics."""
        try:
            collection_stats = self.memory_system.get_collection_stats()

            # Calculate total documents
            total_documents = sum(
                coll.get('count', 0)
                for coll in collection_stats.get('collections', {}).values()
                if isinstance(coll, dict)
            )

            # Get deduplication stats if available
            dedup_stats = {}
            if hasattr(self.memory_system, 'deduplicator') and \
               self.memory_system.deduplicator.enabled:
                dedup_stats = self.memory_system.deduplicator.get_deduplication_stats()

            # Calculate system uptime
            uptime_seconds = time.time() - self.system_start_time
            uptime_hours = uptime_seconds / 3600

            # Count active collections
            active_collections = len([
                coll for coll in collection_stats.get('collections', {}).values()
                if isinstance(coll, dict) and coll.get('status') == 'active'
            ])

            efficiency = dedup_stats.get('deduplication_efficiency', 0) if dedup_stats else 0

            return {
                'total_documents': total_documents,
                'active_collections': active_collections,
                'uptime_hours': round(uptime_hours, 2),
                'deduplication_enabled': bool(dedup_stats),
                'storage_efficiency': efficiency,
                'query_monitoring_active': hasattr(self.memory_system, 'query_monitor'),
                'relationship_tracking_active': hasattr(self.memory_system, 'chunk_manager'),
                'estimated_storage_mb': self._estimate_storage_usage(total_documents),
                'system_maturity': self._calculate_system_maturity(),
            }

        except Exception as e:
            logging.error(f"Failed to generate system overview: {e}")
            return {'error': str(e)}

    def _analyze_storage_patterns(self) -> Dict[str, Any]:
        """Analyze storage usage patterns."""
        try:
            collection_stats = self.memory_system.get_collection_stats()
            collections = collection_stats.get('collections', {})

            # Get document counts per collection
            collection_sizes = {
                name: coll.get('count', 0)
                for name, coll in collections.items()
                if isinstance(coll, dict)
            }

            total_docs = sum(collection_sizes.values())

            # Calculate distribution
            distribution = {}
            if total_docs > 0:
                for name, size in collection_sizes.items():
                    percentage = (size / total_docs) * 100
                    coll_status = collections[name].get('status', 'unknown')
                    distribution[name] = {
                        'document_count': size,
                        'percentage': round(percentage, 2),
                        'status': coll_status if name in collections else 'unknown'
                    }

            # Generate recommendations
            recommendations = []
            if total_docs > 10000:
                recommendations.append(
                    "Consider reviewing retention policies for large collection"
                )

            short_term_count = collection_sizes.get('short_term_memory', 0)
            if total_docs > 0 and (short_term_count / total_docs) > 0.8:
                recommendations.append(
                    "Short-term memory dominant - consider promoting important memories"
                )

            return {
                'total_documents': total_docs,
                'collection_distribution': distribution,
                'recommendations': recommendations,
            }

        except Exception as e:
            logging.error(f"Failed to analyze storage patterns: {e}")
            return {'error': str(e)}

    def _analyze_deduplication_effectiveness(self) -> Dict[str, Any]:
        """Analyze deduplication system effectiveness."""
        try:
            has_deduplicator = hasattr(self.memory_system, 'deduplicator')
            if not has_deduplicator or not self.memory_system.deduplicator.enabled:
                return {
                    'enabled': False,
                    'message': 'Deduplication system not enabled'
                }

            # Get real deduplication statistics
            dedup_stats = self.memory_system.deduplicator.get_deduplication_stats()

            # Get relationship statistics if available
            relationship_stats = {}
            if hasattr(self.memory_system, 'chunk_manager'):
                relationship_stats = \
                    self.memory_system.chunk_manager.get_relationship_statistics()

            return {
                'enabled': True,
                'current_stats': dedup_stats,
                'relationship_stats': relationship_stats,
            }

        except Exception as e:
            logging.error(f"Failed to analyze deduplication effectiveness: {e}")
            return {'error': str(e)}

    def _analyze_query_patterns(self) -> Dict[str, Any]:
        """Analyze query performance metrics."""
        try:
            if not hasattr(self.memory_system, 'query_monitor'):
                return {
                    'enabled': False,
                    'message': 'Query monitoring not enabled'
                }

            # Get real query performance statistics
            daily_stats = self.memory_system.get_query_performance_stats('day')
            weekly_stats = self.memory_system.get_query_performance_stats('week')

            return {
                'enabled': True,
                'daily_performance': daily_stats,
                'weekly_performance': weekly_stats,
            }

        except Exception as e:
            logging.error(f"Failed to analyze query patterns: {e}")
            return {'error': str(e)}

    def _generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate actionable optimization recommendations based on system state."""
        recommendations: List[Dict[str, Any]] = []
        current_time = time.time()

        try:
            system_overview = self._generate_system_overview()

            # Recommendation: Enable deduplication if not enabled and have many documents
            if system_overview.get('total_documents', 0) > 500:
                if not system_overview.get('deduplication_enabled', False):
                    recommendations.append({
                        'priority': 'high',
                        'category': 'storage',
                        'title': 'Enable Deduplication',
                        'description': (
                            'You have many documents but deduplication is disabled. '
                            'Enabling it could reduce storage by 20-40%.'
                        ),
                        'action': 'Enable deduplication in configuration',
                    })
                elif system_overview.get('storage_efficiency', 0) < 15:
                    efficiency = system_overview.get('storage_efficiency', 0)
                    recommendations.append({
                        'priority': 'medium',
                        'category': 'optimization',
                        'title': 'Tune Deduplication Thresholds',
                        'description': (
                            f"Deduplication efficiency is {efficiency}%. "
                            "Consider adjusting similarity thresholds."
                        ),
                        'action': 'Adjust similarity_threshold in deduplication config',
                    })

            # Recommendation: Query performance
            if hasattr(self.memory_system, 'query_monitor'):
                query_stats = self.memory_system.get_query_performance_stats('day')
                if query_stats.get('query_count', 0) > 0:
                    avg_response = query_stats.get(
                        'response_time_stats', {}
                    ).get('mean_ms', 0)
                    if avg_response > 500:
                        recommendations.append({
                            'priority': 'medium',
                            'category': 'performance',
                            'title': 'Slow Query Response Times',
                            'description': (
                                f'Average query response time is {avg_response:.0f}ms. '
                                'Consider enabling smart routing or reducing collection size.'
                            ),
                            'action': 'Review query patterns and collection sizes',
                        })

            # Recommendation: Enable relationship tracking
            if not hasattr(self.memory_system, 'chunk_manager'):
                if system_overview.get('total_documents', 0) > 100:
                    recommendations.append({
                        'priority': 'low',
                        'category': 'features',
                        'title': 'Enable Chunk Relationship Tracking',
                        'description': (
                            'Relationship tracking can improve context preservation '
                            'in query results.'
                        ),
                        'action': 'Enable chunk_relationships in configuration',
                    })

            # Add metadata to recommendations
            for i, rec in enumerate(recommendations):
                rec['id'] = f"rec_{int(current_time)}_{i}"
                rec['generated_at'] = current_time

            return recommendations

        except Exception as e:
            logging.error(f"Failed to generate optimization recommendations: {e}")
            return []

    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess system health based on real metrics."""
        try:
            health_scores = []
            health_factors = {}

            # Storage health - based on collection status
            collection_stats = self.memory_system.get_collection_stats()
            collections = collection_stats.get('collections', {})
            active_count = sum(
                1 for c in collections.values()
                if isinstance(c, dict) and c.get('status') == 'active'
            )
            total_collections = len([
                c for c in collections.values() if isinstance(c, dict)
            ])

            if total_collections > 0:
                storage_score = active_count / total_collections
                health_factors['storage'] = {
                    'score': storage_score,
                    'active_collections': active_count,
                    'total_collections': total_collections,
                }
                health_scores.append(storage_score)

            # Performance health - based on query response times
            if hasattr(self.memory_system, 'query_monitor'):
                query_stats = self.memory_system.get_query_performance_stats('day')
                if query_stats.get('query_count', 0) > 0:
                    avg_response = query_stats.get(
                        'response_time_stats', {}
                    ).get('mean_ms', 0)
                    # Score: 1.0 for <100ms, 0.5 for 500ms, 0.3 for >1000ms
                    if avg_response <= 100:
                        perf_score = 1.0
                    elif avg_response >= 1000:
                        perf_score = 0.3
                    else:
                        perf_score = 1.0 - ((avg_response - 100) / 900) * 0.7

                    health_factors['performance'] = {
                        'score': round(perf_score, 2),
                        'avg_response_ms': round(avg_response, 2),
                        'query_count': query_stats.get('query_count', 0),
                    }
                    health_scores.append(perf_score)

            # Deduplication health
            has_dedup = hasattr(self.memory_system, 'deduplicator')
            if has_dedup and self.memory_system.deduplicator.enabled:
                dedup_stats = self.memory_system.deduplicator.get_deduplication_stats()
                efficiency = dedup_stats.get('deduplication_efficiency', 0)
                # Score based on efficiency (higher is better, 0 is fine if no duplicates)
                dedup_score = min(1.0, 0.7 + (efficiency / 100) * 0.3)
                health_factors['deduplication'] = {
                    'score': round(dedup_score, 2),
                    'efficiency': efficiency,
                }
                health_scores.append(dedup_score)

            # Calculate overall health
            overall_score = statistics.mean(health_scores) if health_scores else 0.7

            # Determine status
            if overall_score >= 0.9:
                status = 'excellent'
            elif overall_score >= 0.75:
                status = 'good'
            elif overall_score >= 0.5:
                status = 'fair'
            else:
                status = 'needs_attention'

            return {
                'overall_score': round(overall_score, 3),
                'status': status,
                'health_factors': health_factors,
            }

        except Exception as e:
            logging.error(f"Failed to assess system health: {e}")
            return {'error': str(e), 'status': 'unknown', 'overall_score': 0}

    def _estimate_storage_usage(self, document_count: int) -> float:
        """Estimate storage usage in MB based on document count."""
        # Rough estimate: ~1.5KB per document including metadata and embeddings
        return round((document_count * 1.5) / 1024, 2)

    def _calculate_system_maturity(self) -> str:
        """Calculate system maturity level based on enabled features."""
        has_dedup = hasattr(self.memory_system, 'deduplicator') and \
            self.memory_system.deduplicator.enabled
        has_monitor = hasattr(self.memory_system, 'query_monitor')
        has_chunks = hasattr(self.memory_system, 'chunk_manager')

        features_enabled = [has_dedup, has_monitor, has_chunks]

        feature_count = sum(features_enabled)
        if feature_count == 3:
            return 'advanced'
        elif feature_count == 2:
            return 'intermediate'
        elif feature_count == 1:
            return 'basic'
        else:
            return 'minimal'

    def _cleanup_analytics_history(self) -> None:
        """Cleanup old analytics history based on retention policy."""
        if not self.analytics_history:
            return

        retention_seconds = self.config.get('history_retention_days', 30) * 24 * 3600
        cutoff_time = time.time() - retention_seconds

        self.analytics_history = [
            entry for entry in self.analytics_history
            if entry.get('timestamp', 0) > cutoff_time
        ]
