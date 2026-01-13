"""
Advanced Deduplication Features

Implements domain-aware deduplication thresholds, semantic clustering for broader similarity detection,
and automated threshold optimization based on performance metrics.
"""

import time
import logging
import statistics
from typing import Dict, Any, List, Tuple, Optional


class AdvancedDeduplicationFeatures:
    """Advanced features for the deduplication system."""

    def __init__(self, deduplicator: Any, advanced_config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize advanced deduplication features.

        Args:
            deduplicator: Reference to MemoryDeduplicator
            advanced_config: Configuration for advanced features
        """
        self.deduplicator = deduplicator
        self.config = advanced_config or self._get_default_config()

        # Domain-specific thresholds
        self.domain_thresholds: Dict[str, float] = self.config.get('domain_thresholds', {})

        # Effectiveness tracking
        self.effectiveness_history: List[Dict[str, Any]] = []

        # Semantic clustering
        self.semantic_clusters: Dict[str, Any] = {}

        # Auto-optimization
        self.threshold_optimization_history: List[Dict[str, Any]] = []

    def _get_default_config(self) -> dict:
        """Default configuration for advanced features."""
        return {
            'enable_domain_aware_thresholds': True,
            'enable_semantic_clustering': True,
            'enable_auto_optimization': True,
            'domain_thresholds': {
                'code': 0.85,      # Code is more variable, lower threshold
                'text': 0.95,      # Text needs high similarity
                'data': 0.90,      # Data structures medium similarity
                'documentation': 0.80  # Documentation can vary more
            },
            'semantic_clustering': {
                'cluster_threshold': 0.70,
                'min_cluster_size': 2,
                'max_clusters': 50,
                'cluster_refresh_hours': 24
            },
            'auto_optimization': {
                'optimization_interval_hours': 168,  # Weekly
                'performance_window_hours': 72,      # 3 days
                'effectiveness_target': 0.25,       # 25% target effectiveness
                'adjustment_step': 0.02              # 2% threshold adjustments
            }
        }

    def apply_domain_aware_thresholds(self, documents: List[Dict[str, Any]],
                                      base_threshold: float) -> List[Tuple[float, str]]:
        """Apply domain-specific similarity thresholds.

        Args:
            documents: List of document dictionaries
            base_threshold: Base similarity threshold

        Returns:
            List of (threshold, reason) tuples for each document
        """
        if not self.config.get('enable_domain_aware_thresholds', True):
            return [(base_threshold, 'base_threshold')] * len(documents)

        thresholds = []

        for doc in documents:
            threshold = base_threshold
            reason = 'base_threshold'

            try:
                # Determine document domain from metadata or content
                domain = self._classify_document_domain(doc)

                if domain in self.domain_thresholds:
                    threshold = self.domain_thresholds[domain]
                    reason = f'domain_{domain}'

                # Apply content-specific adjustments
                content_adjustments = self._calculate_content_adjustments(doc)
                threshold += content_adjustments['adjustment']
                reason += f"_adjusted_{content_adjustments['reason']}"

                # Ensure threshold stays within reasonable bounds
                threshold = max(0.5, min(0.99, threshold))

            except Exception as e:
                logging.warning(f"Failed to apply domain-aware threshold: {e}")

            thresholds.append((threshold, reason))

        return thresholds

    def _classify_document_domain(self, doc: Dict[str, Any]) -> str:
        """Classify document domain based on content and metadata."""
        content = doc.get('page_content', '')
        metadata = doc.get('metadata', {})

        # Check explicit domain in metadata
        if 'domain' in metadata:
            return str(metadata['domain'])

        # Check language field for code
        language = metadata.get('language', '').lower()
        if language in ['python', 'javascript', 'java', 'c++', 'c', 'go', 'rust']:
            return 'code'

        # Content-based classification
        code_indicators = ['def ', 'function ', 'class ', 'import ', 'from ', '{', '}', ');']
        if sum(1 for indicator in code_indicators if indicator in content) >= 3:
            return 'code'

        data_indicators = ['json', 'xml', 'csv', '":', '{}', '[]', 'data:']
        if sum(1 for indicator in data_indicators if indicator.lower() in content.lower()) >= 2:
            return 'data'

        doc_indicators = ['# ', '## ', 'README', 'documentation', 'guide', 'manual']
        if sum(1 for indicator in doc_indicators if indicator in content) >= 1:
            return 'documentation'

        return 'text'  # Default domain

    def _calculate_content_adjustments(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate threshold adjustments based on content characteristics."""
        content = doc.get('page_content', '')
        metadata = doc.get('metadata', {})

        adjustment = 0.0
        reasons = []

        # Length adjustment - longer content might need lower threshold
        content_length = len(content)
        if content_length > 2000:
            adjustment -= 0.02
            reasons.append('long_content')
        elif content_length < 200:
            adjustment += 0.02
            reasons.append('short_content')

        # Importance adjustment - important content needs higher threshold
        importance = metadata.get('importance_score', 0.5)
        if importance > 0.8:
            adjustment += 0.03
            reasons.append('high_importance')
        elif importance < 0.3:
            adjustment -= 0.02
            reasons.append('low_importance')

        # Access count adjustment - frequently accessed content needs higher threshold
        access_count = metadata.get('access_count', 0)
        if access_count > 10:
            adjustment += 0.02
            reasons.append('high_access')

        return {
            'adjustment': adjustment,
            'reason': '_'.join(reasons) if reasons else 'no_adjustment'
        }

    def perform_semantic_clustering(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform semantic clustering for broader similarity detection.

        Args:
            documents: List of document dictionaries

        Returns:
            Clustering results with cluster information
        """
        if not self.config.get('enable_semantic_clustering', True):
            return {'enabled': False, 'message': 'Semantic clustering disabled'}

        start_time = time.time()
        clustering_config = self.config.get('semantic_clustering', self._get_default_config()['semantic_clustering'])

        try:
            # Use similarity calculator to find relationships
            similarity_pairs = self.deduplicator.similarity_calculator.find_duplicates_batch(
                documents,
                threshold=clustering_config['cluster_threshold']
            )

            # Build cluster graph
            clusters = self._build_semantic_clusters(similarity_pairs, clustering_config)

            # Analyze clusters
            cluster_analysis = self._analyze_semantic_clusters(clusters)

            # Store clusters for future reference
            cluster_id = f"cluster_{int(time.time())}"
            self.semantic_clusters[cluster_id] = {
                'timestamp': time.time(),
                'clusters': clusters,
                'analysis': cluster_analysis,
                'document_count': len(documents),
                'processing_time': time.time() - start_time
            }

            # Cleanup old clusters
            self._cleanup_old_clusters()

            return {
                'enabled': True,
                'cluster_id': cluster_id,
                'clusters_found': len(clusters),
                'documents_clustered': sum(len(cluster) for cluster in clusters),
                'processing_time': time.time() - start_time,
                'cluster_analysis': cluster_analysis
            }

        except Exception as e:
            logging.error(f"Failed to perform semantic clustering: {e}")
            return {'enabled': True, 'error': str(e)}

    def _build_semantic_clusters(self, similarity_pairs: List[tuple],
                                 clustering_config: dict) -> List[List[Dict[str, Any]]]:
        """Build clusters from similarity pairs using graph-based clustering."""
        clusters: List[List[Dict[str, Any]]] = []
        doc_to_cluster: Dict[int, List[Dict[str, Any]]] = {}

        for doc1_data, doc2_data, similarity in similarity_pairs:
            doc1 = doc1_data['document'] if 'document' in doc1_data else doc1_data
            doc2 = doc2_data['document'] if 'document' in doc2_data else doc2_data

            doc1_id = id(doc1)
            doc2_id = id(doc2)

            cluster1 = doc_to_cluster.get(doc1_id)
            cluster2 = doc_to_cluster.get(doc2_id)

            if cluster1 is None and cluster2 is None:
                # Create new cluster
                new_cluster = [doc1, doc2]
                clusters.append(new_cluster)
                doc_to_cluster[doc1_id] = new_cluster
                doc_to_cluster[doc2_id] = new_cluster

            elif cluster1 is None:
                # Add doc1 to doc2's cluster
                assert cluster2 is not None
                cluster2.append(doc1)
                doc_to_cluster[doc1_id] = cluster2

            elif cluster2 is None:
                # Add doc2 to doc1's cluster
                assert cluster1 is not None
                cluster1.append(doc2)
                doc_to_cluster[doc2_id] = cluster1

            elif cluster1 != cluster2:
                # Merge clusters
                cluster1.extend(cluster2)
                for doc in cluster2:
                    doc_to_cluster[id(doc)] = cluster1
                clusters.remove(cluster2)

        # Filter clusters by minimum size
        min_size = clustering_config.get('min_cluster_size', 2)
        filtered_clusters = [c for c in clusters if len(c) >= min_size]

        # Limit number of clusters
        max_clusters = clustering_config.get('max_clusters', 50)
        if len(filtered_clusters) > max_clusters:
            # Keep largest clusters
            filtered_clusters.sort(key=len, reverse=True)
            filtered_clusters = filtered_clusters[:max_clusters]

        return filtered_clusters

    def _analyze_semantic_clusters(self, clusters: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze semantic clusters for insights."""
        if not clusters:
            return {'cluster_count': 0, 'insights': []}

        cluster_sizes = [len(cluster) for cluster in clusters]

        avg_cluster_size = statistics.mean(cluster_sizes)
        largest_cluster_size = max(cluster_sizes)
        cluster_count = len(clusters)
        
        analysis: Dict[str, Any] = {
            'cluster_count': cluster_count,
            'total_documents_in_clusters': sum(cluster_sizes),
            'average_cluster_size': avg_cluster_size,
            'largest_cluster_size': largest_cluster_size,
            'cluster_size_distribution': {
                'small': len([s for s in cluster_sizes if s <= 3]),
                'medium': len([s for s in cluster_sizes if 4 <= s <= 10]),
                'large': len([s for s in cluster_sizes if s > 10])
            }
        }

        # Generate insights
        insights: List[str] = []
        if avg_cluster_size > 5:
            insights.append("Large clusters detected - consider reviewing similarity thresholds")
        if cluster_count > 20:
            insights.append("Many clusters found - potential for significant optimization")
        if largest_cluster_size > 15:
            insights.append("Very large cluster detected - may indicate overly broad similarity")

        analysis['insights'] = insights
        return analysis

    def _cleanup_old_clusters(self) -> None:
        """Remove old semantic clusters based on retention policy."""
        current_time = time.time()
        clustering_config = self.config.get('semantic_clustering', self._get_default_config()['semantic_clustering'])
        retention_hours = clustering_config.get('cluster_refresh_hours', 24)
        cutoff_time = current_time - (retention_hours * 3600)

        clusters_to_remove = [
            cluster_id for cluster_id, cluster_data in self.semantic_clusters.items()
            if cluster_data['timestamp'] < cutoff_time
        ]

        for cluster_id in clusters_to_remove:
            del self.semantic_clusters[cluster_id]

    def optimize_thresholds_automatically(self) -> Dict[str, Any]:
        """Automatically optimize deduplication thresholds based on performance metrics.

        Returns:
            Optimization results and recommendations
        """
        if not self.config.get('enable_auto_optimization', True):
            return {'enabled': False, 'message': 'Auto-optimization disabled'}

        start_time = time.time()

        try:
            # Gather performance data
            performance_data = self._gather_performance_data()

            # Analyze current effectiveness
            current_effectiveness = self._calculate_current_effectiveness(performance_data)

            # Determine optimization direction
            optimization_strategy = self._determine_optimization_strategy(
                current_effectiveness, performance_data
            )

            # Apply threshold adjustments
            adjustments = self._apply_threshold_adjustments(optimization_strategy)

            # Record optimization attempt
            optimization_record = {
                'timestamp': time.time(),
                'current_effectiveness': current_effectiveness,
                'strategy': optimization_strategy,
                'adjustments_made': adjustments,
                'processing_time': time.time() - start_time
            }

            self.threshold_optimization_history.append(optimization_record)

            # Cleanup old history
            self._cleanup_optimization_history()

            return {
                'enabled': True,
                'optimization_applied': len(adjustments) > 0,
                'current_effectiveness': current_effectiveness,
                'adjustments_made': adjustments,
                'strategy': optimization_strategy,
                'processing_time': time.time() - start_time,
                'next_optimization': self._calculate_next_optimization_time()
            }

        except Exception as e:
            logging.error(f"Failed to optimize thresholds automatically: {e}")
            return {'enabled': True, 'error': str(e)}

    def _gather_performance_data(self) -> Dict[str, Any]:
        """Gather performance data for optimization analysis."""
        # Get basic deduplication statistics without calling get_deduplication_stats() to avoid recursion
        dedup_stats = {
            'total_duplicates_found': self.deduplicator.stats.get('total_duplicates_found', 0),
            'total_documents_merged': self.deduplicator.stats.get('total_documents_merged', 0),
            'total_storage_saved': self.deduplicator.stats.get('total_storage_saved', 0),
            'enabled': self.deduplicator.enabled,
            'similarity_threshold': self.deduplicator.similarity_threshold
        }

        # Get recent effectiveness history
        recent_effectiveness = self.effectiveness_history[-10:] if self.effectiveness_history else []

        return {
            'dedup_stats': dedup_stats,
            'recent_effectiveness': recent_effectiveness,
            'current_threshold': self.deduplicator.similarity_threshold,
            'domain_thresholds': self.domain_thresholds.copy()
        }

    def _calculate_current_effectiveness(self, performance_data: Dict[str, Any]) -> float:
        """Calculate current deduplication effectiveness."""
        dedup_stats = performance_data['dedup_stats']
        efficiency = dedup_stats.get('deduplication_efficiency', 0)
        return float(efficiency) / 100.0

    def _determine_optimization_strategy(self, current_effectiveness: float,
                                         performance_data: Dict[str, Any]) -> str:
        """Determine the optimization strategy based on current performance."""
        auto_opt_config = self.config.get('auto_optimization', self._get_default_config()['auto_optimization'])
        target_effectiveness = auto_opt_config.get('effectiveness_target', 0.25)

        if current_effectiveness < target_effectiveness * 0.7:
            return 'increase_sensitivity'  # Lower thresholds to catch more duplicates
        elif current_effectiveness > target_effectiveness * 1.3:
            return 'decrease_sensitivity'  # Raise thresholds to avoid false positives
        else:
            return 'fine_tune'  # Make small adjustments

    def _apply_threshold_adjustments(self, strategy: str) -> List[Dict[str, Any]]:
        """Apply threshold adjustments based on optimization strategy."""
        adjustments = []
        auto_opt_config = self.config.get('auto_optimization', self._get_default_config()['auto_optimization'])
        step_size = auto_opt_config.get('adjustment_step', 0.02)

        if strategy == 'increase_sensitivity':
            # Lower thresholds to catch more duplicates
            new_base_threshold = max(0.7, self.deduplicator.similarity_threshold - step_size)
            adjustments.append({
                'type': 'base_threshold',
                'old_value': self.deduplicator.similarity_threshold,
                'new_value': new_base_threshold,
                'reason': 'increase_sensitivity'
            })
            self.deduplicator.similarity_threshold = new_base_threshold

            # Also adjust domain thresholds
            for domain in self.domain_thresholds:
                old_value = self.domain_thresholds[domain]
                new_value = max(0.6, old_value - step_size)
                if new_value != old_value:
                    self.domain_thresholds[domain] = new_value
                    adjustments.append({
                        'type': f'domain_threshold_{domain}',
                        'old_value': old_value,
                        'new_value': new_value,
                        'reason': 'increase_sensitivity'
                    })

        elif strategy == 'decrease_sensitivity':
            # Raise thresholds to reduce false positives
            new_base_threshold = min(0.98, self.deduplicator.similarity_threshold + step_size)
            adjustments.append({
                'type': 'base_threshold',
                'old_value': self.deduplicator.similarity_threshold,
                'new_value': new_base_threshold,
                'reason': 'decrease_sensitivity'
            })
            self.deduplicator.similarity_threshold = new_base_threshold

            # Also adjust domain thresholds
            for domain in self.domain_thresholds:
                old_value = self.domain_thresholds[domain]
                new_value = min(0.99, old_value + step_size)
                if new_value != old_value:
                    self.domain_thresholds[domain] = new_value
                    adjustments.append({
                        'type': f'domain_threshold_{domain}',
                        'old_value': old_value,
                        'new_value': new_value,
                        'reason': 'decrease_sensitivity'
                    })

        elif strategy == 'fine_tune':
            # Make small adjustments to specific domains based on performance
            half_step = step_size / 2

            # This is a simplified fine-tuning approach
            # In production, you'd want more sophisticated analysis
            for domain in self.domain_thresholds:
                if domain == 'code':
                    # Code often benefits from slightly lower thresholds
                    old_value = self.domain_thresholds[domain]
                    new_value = max(0.75, old_value - half_step)
                    if new_value != old_value:
                        self.domain_thresholds[domain] = new_value
                        adjustments.append({
                            'type': f'domain_threshold_{domain}',
                            'old_value': old_value,
                            'new_value': new_value,
                            'reason': 'fine_tune_code'
                        })

        return adjustments

    def _calculate_next_optimization_time(self) -> float:
        """Calculate when the next optimization should run."""
        auto_opt_config = self.config.get('auto_optimization', self._get_default_config()['auto_optimization'])
        interval_hours = auto_opt_config.get('optimization_interval_hours', 168)
        return float(time.time() + (float(interval_hours) * 3600))

    def _cleanup_optimization_history(self) -> None:
        """Cleanup old optimization history."""
        # Keep last 10 optimization records
        if len(self.threshold_optimization_history) > 10:
            self.threshold_optimization_history = self.threshold_optimization_history[-10:]

    def track_effectiveness(self, effectiveness_score: float, context: Optional[Dict[str, Any]] = None) -> None:
        """Track deduplication effectiveness over time.

        Args:
            effectiveness_score: Current effectiveness score (0.0 to 1.0)
            context: Additional context information
        """
        effectiveness_record = {
            'timestamp': time.time(),
            'effectiveness_score': effectiveness_score,
            'context': context or {}
        }

        self.effectiveness_history.append(effectiveness_record)

        # Keep last 100 records
        if len(self.effectiveness_history) > 100:
            self.effectiveness_history = self.effectiveness_history[-100:]

    def get_advanced_features_stats(self) -> Dict[str, Any]:
        """Get statistics about advanced deduplication features."""
        current_time = time.time()

        stats = {
            'domain_aware_thresholds': {
                'enabled': self.config.get('enable_domain_aware_thresholds', True),
                'domain_count': len(self.domain_thresholds),
                'domain_thresholds': self.domain_thresholds.copy()
            },
            'semantic_clustering': {
                'enabled': self.config.get('enable_semantic_clustering', True),
                'active_clusters': len(self.semantic_clusters),
                'total_clusters_created': len(self.semantic_clusters)
            },
            'auto_optimization': {
                'enabled': self.config.get('enable_auto_optimization', True),
                'optimizations_performed': len(self.threshold_optimization_history),
                'last_optimization': (
                    self.threshold_optimization_history[-1]['timestamp']
                    if self.threshold_optimization_history else None
                ),
                'next_optimization_due': self._calculate_next_optimization_time() <= current_time
            },
            'effectiveness_tracking': {
                'records_count': len(self.effectiveness_history),
                'current_effectiveness': (
                    self.effectiveness_history[-1]['effectiveness_score']
                    if self.effectiveness_history else None
                ),
                'trend': self._calculate_effectiveness_trend()
            }
        }

        return stats

    def _calculate_effectiveness_trend(self) -> str:
        """Calculate the trend of effectiveness over recent history."""
        if len(self.effectiveness_history) < 3:
            return 'insufficient_data'

        recent_scores = [record['effectiveness_score'] for record in self.effectiveness_history[-5:]]

        if len(recent_scores) >= 2:
            recent_avg = statistics.mean(recent_scores[-3:])
            older_avg = statistics.mean(recent_scores[:-3]) if len(recent_scores) > 3 else recent_scores[0]

            if recent_avg > older_avg * 1.1:
                return 'improving'
            elif recent_avg < older_avg * 0.9:
                return 'declining'
            else:
                return 'stable'

        return 'stable'

    def get_performance_analytics(self) -> Dict[str, Any]:
        """Get performance analytics for the advanced deduplication features.

        Returns:
            Dictionary containing performance analytics and metrics
        """
        performance_data = self._gather_performance_data()
        current_effectiveness = self._calculate_current_effectiveness(performance_data)

        return {
            'performance_analytics': {
                'effectiveness_score': current_effectiveness,
                'performance_data': performance_data,
                'effectiveness_trend': self._calculate_effectiveness_trend(),
                'optimization_history': {
                    'total_optimizations': len(self.threshold_optimization_history),
                    'recent_optimizations': (
                        self.threshold_optimization_history[-3:]
                        if self.threshold_optimization_history else []
                    ),
                    'last_optimization': (
                        self.threshold_optimization_history[-1]
                        if self.threshold_optimization_history else None
                    )
                },
                'domain_performance': {
                    'domain_thresholds': self.domain_thresholds.copy(),
                    'effectiveness_by_domain': self._calculate_domain_effectiveness()
                },
                'clustering_metrics': {
                    'active_clusters': len(self.semantic_clusters),
                    'total_clustered_documents': sum(
                        len(cluster['documents']) for cluster in self.semantic_clusters.values()
                    ),
                    'cluster_quality_scores': [
                        cluster.get('quality_score', 0.0)
                        for cluster in self.semantic_clusters.values()
                    ]
                }
            }
        }

    def _calculate_domain_effectiveness(self) -> Dict[str, float]:
        """Calculate effectiveness scores by document domain."""
        if not self.effectiveness_history:
            return {}

        # Group effectiveness records by domain if available
        domain_scores: Dict[str, List[float]] = {}
        for record in self.effectiveness_history[-10:]:  # Last 10 records
            context = record.get('context', {})
            domain = context.get('domain', 'unknown')

            if domain not in domain_scores:
                domain_scores[domain] = []
            domain_scores[domain].append(record['effectiveness_score'])

        # Calculate average effectiveness per domain
        domain_effectiveness: Dict[str, float] = {}
        for domain, scores in domain_scores.items():
            domain_effectiveness[domain] = statistics.mean(scores) if scores else 0.0

        return domain_effectiveness
