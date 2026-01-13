"""
Query Performance Monitoring

Tracks query performance improvements from deduplication and other optimizations.
Provides insights into system efficiency and user experience.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Deque, DefaultDict
from collections import defaultdict, deque
import statistics


class QueryPerformanceMonitor:
    """Monitors query performance and tracks improvements from deduplication."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize query performance monitor.

        Args:
            config: Configuration for performance monitoring
        """
        self.config = config or self._get_default_config()

        # Performance tracking
        self.query_history: Deque[Dict[str, Any]] = deque(maxlen=self.config['history_size'])
        self.performance_metrics: DefaultDict[str, List[Any]] = defaultdict(list)

        # Statistics aggregation
        self.hourly_stats: DefaultDict[int, DefaultDict[str, List[Any]]] = defaultdict(lambda: defaultdict(list))
        self.daily_stats: DefaultDict[int, DefaultDict[str, List[Any]]] = defaultdict(lambda: defaultdict(list))

        # Start time for relative measurements
        self.start_time = time.time()

    def _get_default_config(self) -> dict:
        """Default configuration for query monitoring."""
        return {
            'history_size': 1000,
            'track_user_satisfaction': True,
            'enable_real_time_metrics': True,
            'aggregation_intervals': {
                'hourly': 3600,
                'daily': 86400
            },
            'performance_thresholds': {
                'fast_query_ms': 100,
                'slow_query_ms': 1000,
                'good_result_quality': 0.8
            }
        }

    def track_query(self, query: str, results: Dict[str, Any], processing_time: float,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Track a query execution and its results.

        Args:
            query: The search query
            results: Query results dictionary
            processing_time: Time taken to process query in seconds
            metadata: Additional metadata about the query

        Returns:
            Query tracking ID
        """
        query_id = f"q_{int(time.time() * 1000)}_{len(self.query_history)}"
        current_time = time.time()

        # Create query record
        query_record = {
            'id': query_id,
            'timestamp': current_time,
            'query': query,
            'processing_time_ms': processing_time * 1000,
            'total_results': results.get('total_results', 0),
            'collections_searched': results.get('collections_searched', []),
            'smart_routing_used': results.get('smart_routing_used', False),
            'query_optimization_applied': results.get('query_optimization_applied', False),
            'metadata': metadata or {}
        }

        # Calculate performance metrics
        self._calculate_query_metrics(query_record, results)

        # Store in history
        self.query_history.append(query_record)

        # Update aggregated statistics
        self._update_aggregated_stats(query_record)

        logging.debug(
            f"Tracked query {query_id}: {
                processing_time *
                1000:.1f}ms, {
                query_record['total_results']} results")

        return query_id

    def _calculate_query_metrics(self, query_record: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Calculate performance metrics for a query."""
        processing_time_ms = query_record['processing_time_ms']

        # Response time classification
        if processing_time_ms < self.config['performance_thresholds']['fast_query_ms']:
            query_record['response_category'] = 'fast'
        elif processing_time_ms < self.config['performance_thresholds']['slow_query_ms']:
            query_record['response_category'] = 'medium'
        else:
            query_record['response_category'] = 'slow'

        # Result quality estimation
        query_record['result_quality_score'] = self._estimate_result_quality(query_record, results)

        # Deduplication impact analysis
        query_record['deduplication_impact'] = self._analyze_deduplication_impact(results)

        # Efficiency metrics
        query_record['results_per_ms'] = query_record['total_results'] / max(processing_time_ms, 1)
        query_record['collections_efficiency'] = query_record['total_results'] / \
            max(len(query_record['collections_searched']), 1)

    def _estimate_result_quality(self, query_record: dict, results: dict) -> float:
        """Estimate result quality based on various factors."""
        quality_score = 0.5  # Base quality

        # Boost for getting results
        if query_record['total_results'] > 0:
            quality_score += 0.2

        # Boost for reasonable number of results (not too few, not too many)
        result_count = query_record['total_results']
        if 3 <= result_count <= 10:
            quality_score += 0.1
        elif result_count > 20:
            quality_score -= 0.1  # Too many might indicate poor filtering

        # Boost for smart routing usage
        if query_record['smart_routing_used']:
            quality_score += 0.1

        # Boost for optimization
        if query_record['query_optimization_applied']:
            quality_score += 0.05

        # Analyze result diversity (if available)
        if 'content' in results:
            diversity_score = self._calculate_result_diversity(results['content'])
            quality_score += diversity_score * 0.15

        return min(quality_score, 1.0)

    def _calculate_result_diversity(self, content_blocks: List[dict]) -> float:
        """Calculate diversity of results (simplified)."""
        if not content_blocks or len(content_blocks) < 2:
            return 0.5

        # Simple diversity based on text length variation
        lengths = [len(block.get('text', '')) for block in content_blocks]
        if len(set(lengths)) > 1:
            return min(statistics.stdev(lengths) / statistics.mean(lengths), 1.0)

        return 0.5

    def _analyze_deduplication_impact(self, results: dict) -> dict:
        """Analyze the impact of deduplication on query results."""
        impact = {
            'merged_documents_found': 0,
            'total_source_documents': 0,
            'deduplication_hit_rate': 0.0
        }

        try:
            if 'content' in results:
                for block in results['content']:
                    text = block.get('text', '')
                    # Look for deduplication markers
                    if 'Merged from' in text:
                        impact['merged_documents_found'] += 1
                        # Extract source count if possible
                        try:
                            parts = text.split('Merged from ')
                            if len(parts) > 1:
                                source_part = parts[1].split(' sources')[0]
                                impact['total_source_documents'] += int(source_part)
                        except BaseException:
                            impact['total_source_documents'] += 2  # Assume at least 2 sources

                # Calculate hit rate
                total_results = len(results['content'])
                if total_results > 0:
                    impact['deduplication_hit_rate'] = impact['merged_documents_found'] / total_results

        except Exception as e:
            logging.warning(f"Failed to analyze deduplication impact: {e}")

        return impact

    def _update_aggregated_stats(self, query_record: Dict[str, Any]) -> None:
        """Update hourly and daily aggregated statistics."""
        current_time = query_record['timestamp']
        hour_key = int(current_time // 3600)
        day_key = int(current_time // 86400)

        # Hourly aggregation
        self.hourly_stats[hour_key]['response_times'].append(query_record['processing_time_ms'])
        self.hourly_stats[hour_key]['result_counts'].append(query_record['total_results'])
        self.hourly_stats[hour_key]['quality_scores'].append(query_record['result_quality_score'])
        self.hourly_stats[hour_key]['dedup_hit_rates'].append(
            query_record['deduplication_impact']['deduplication_hit_rate'])

        # Daily aggregation
        self.daily_stats[day_key]['response_times'].append(query_record['processing_time_ms'])
        self.daily_stats[day_key]['result_counts'].append(query_record['total_results'])
        self.daily_stats[day_key]['quality_scores'].append(query_record['result_quality_score'])
        self.daily_stats[day_key]['dedup_hit_rates'].append(
            query_record['deduplication_impact']['deduplication_hit_rate'])

    def get_performance_summary(self, time_window: str = 'all') -> Dict[str, Any]:
        """Get comprehensive performance summary.

        Args:
            time_window: 'hour', 'day', 'week', or 'all'

        Returns:
            Performance summary dictionary
        """
        current_time = time.time()

        # Filter queries based on time window
        if time_window == 'hour':
            cutoff = current_time - 3600
        elif time_window == 'day':
            cutoff = current_time - 86400
        elif time_window == 'week':
            cutoff = current_time - 604800
        else:
            cutoff = 0

        filtered_queries = [q for q in self.query_history if q['timestamp'] >= cutoff]

        if not filtered_queries:
            return self._empty_summary()

        # Calculate summary statistics
        response_times = [q['processing_time_ms'] for q in filtered_queries]
        result_counts = [q['total_results'] for q in filtered_queries]
        quality_scores = [q['result_quality_score'] for q in filtered_queries]

        # Deduplication statistics
        dedup_impacts = [q['deduplication_impact'] for q in filtered_queries]
        merged_doc_counts = [d['merged_documents_found'] for d in dedup_impacts]
        hit_rates = [d['deduplication_hit_rate'] for d in dedup_impacts]

        # Performance categorization
        fast_queries = len([q for q in filtered_queries if q['response_category'] == 'fast'])
        medium_queries = len([q for q in filtered_queries if q['response_category'] == 'medium'])
        slow_queries = len([q for q in filtered_queries if q['response_category'] == 'slow'])

        summary = {
            'time_window': time_window,
            'query_count': len(filtered_queries),
            'time_range': {
                'start': min(q['timestamp'] for q in filtered_queries),
                'end': max(q['timestamp'] for q in filtered_queries),
                'duration_hours': (current_time - cutoff) / 3600
            },
            'response_time_stats': {
                'mean_ms': statistics.mean(response_times),
                'median_ms': statistics.median(response_times),
                'p95_ms': self._percentile(response_times, 95),
                'min_ms': min(response_times),
                'max_ms': max(response_times)
            },
            'result_stats': {
                'mean_results': statistics.mean(result_counts),
                'median_results': statistics.median(result_counts),
                'total_results_returned': sum(result_counts)
            },
            'quality_metrics': {
                'mean_quality': statistics.mean(quality_scores),
                'median_quality': statistics.median(quality_scores),
                'high_quality_queries': len([
                    q for q in quality_scores
                    if q > self.config['performance_thresholds']['good_result_quality']
                ])
            },
            'performance_distribution': {
                'fast_queries': fast_queries,
                'medium_queries': medium_queries,
                'slow_queries': slow_queries,
                'fast_percentage': fast_queries / len(filtered_queries) * 100
            },
            'deduplication_impact': {
                'queries_with_merged_docs': len([c for c in merged_doc_counts if c > 0]),
                'mean_hit_rate': statistics.mean(hit_rates) if hit_rates else 0.0,
                'total_merged_documents': sum(merged_doc_counts),
                'deduplication_effectiveness': sum(hit_rates) / len(hit_rates) if hit_rates else 0.0
            },
            'optimization_usage': {
                'smart_routing_usage': (
                    len([q for q in filtered_queries if q['smart_routing_used']])
                    / len(filtered_queries) * 100
                ),
                'query_optimization_usage': (
                    len([q for q in filtered_queries if q['query_optimization_applied']])
                    / len(filtered_queries) * 100
                )
            }
        }

        return summary

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index == int(index):
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary when no data available."""
        return {
            'query_count': 0,
            'message': 'No queries in specified time window'
        }

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics."""
        if not self.query_history:
            return {'status': 'no_data', 'message': 'No queries tracked yet'}

        recent_queries = list(self.query_history)[-10:]  # Last 10 queries

        metrics = {
            'last_query_time': recent_queries[-1]['timestamp'],
            'recent_average_response_ms': statistics.mean([q['processing_time_ms'] for q in recent_queries]),
            'recent_quality_score': statistics.mean([q['result_quality_score'] for q in recent_queries]),
            'queries_per_minute': self._calculate_query_rate(),
            'system_health_score': self._calculate_system_health(),
            'active_optimizations': {
                'smart_routing': any(q['smart_routing_used'] for q in recent_queries),
                'query_optimization': any(q['query_optimization_applied'] for q in recent_queries)
            }
        }

        return metrics

    def _calculate_query_rate(self) -> float:
        """Calculate queries per minute over recent period."""
        current_time = time.time()
        minute_ago = current_time - 60

        recent_queries = [q for q in self.query_history if q['timestamp'] >= minute_ago]
        return len(recent_queries)  # Queries in last minute

    def _calculate_system_health(self) -> float:
        """Calculate overall system health score."""
        if not self.query_history:
            return 0.5

        recent_queries = list(self.query_history)[-20:]  # Last 20 queries

        health_score = 0.7  # Base health

        # Response time health
        avg_response = statistics.mean([q['processing_time_ms'] for q in recent_queries])
        if avg_response < 200:
            health_score += 0.2
        elif avg_response < 500:
            health_score += 0.1
        elif avg_response > 1000:
            health_score -= 0.2

        # Quality health
        avg_quality = statistics.mean([q['result_quality_score'] for q in recent_queries])
        health_score += (avg_quality - 0.5) * 0.2  # Adjust based on quality

        # Deduplication health
        dedup_usage = len([q for q in recent_queries if q['deduplication_impact']['merged_documents_found'] > 0])
        if dedup_usage > 0:
            health_score += min(dedup_usage / len(recent_queries) * 0.1, 0.1)

        return float(min(max(health_score, 0.0), 1.0))

    def export_metrics(self, format: str = 'dict') -> Any:
        """Export performance metrics in specified format.

        Args:
            format: Export format ('dict', 'json', 'csv')

        Returns:
            Metrics in requested format
        """
        summary = self.get_performance_summary('all')

        if format == 'dict':
            return summary
        elif format == 'json':
            import json
            return json.dumps(summary, indent=2, default=str)
        elif format == 'csv':
            # Convert to CSV format (simplified)
            csv_data = []
            for query in self.query_history:
                csv_data.append([
                    query['timestamp'],
                    query['processing_time_ms'],
                    query['total_results'],
                    query['result_quality_score'],
                    query['response_category'],
                    query['smart_routing_used'],
                    query['deduplication_impact']['deduplication_hit_rate']
                ])
            return csv_data

        return summary
