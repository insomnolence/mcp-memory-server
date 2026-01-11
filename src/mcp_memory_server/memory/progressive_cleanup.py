"""
Progressive Cleanup Strategy for Memory Management

Implements multi-phase cleanup to avoid performance impact:
- Daily: Quick exact duplicate removal
- Weekly: Similarity-based clustering cleanup
- Monthly: Deep analysis and optimization
"""

import time
import logging
from typing import Dict, Any
from enum import Enum

# Import ChromaDB errors for specific exception handling
try:
    from chromadb.errors import ChromaError
except ImportError:
    ChromaError = Exception

# Custom exceptions available for enhanced error handling
# from .exceptions import CleanupError, DeduplicationError


class CleanupPhase(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ProgressiveCleanupManager:
    """Manages progressive cleanup phases for memory collections."""

    def __init__(self, memory_system, cleanup_config: dict = None):
        """Initialize progressive cleanup manager.

        Args:
            memory_system: Reference to HierarchicalMemorySystem
            cleanup_config: Configuration for cleanup intervals and thresholds
        """
        self.memory_system = memory_system
        self.config = cleanup_config or self._get_default_config()

        # Tracking last cleanup times
        self.last_cleanup = {
            CleanupPhase.DAILY: 0,
            CleanupPhase.WEEKLY: 0,
            CleanupPhase.MONTHLY: 0
        }

        # Load cleanup history if available
        self._load_cleanup_history()

    def _get_default_config(self) -> dict:
        """Default configuration for progressive cleanup."""
        return {
            'daily': {
                'interval_hours': 24,
                'max_processing_time_seconds': 30,
                'duplicate_threshold': 0.95,
                'enabled': True
            },
            'weekly': {
                'interval_hours': 168,  # 7 days
                'max_processing_time_seconds': 300,  # 5 minutes
                'similarity_threshold': 0.75,
                'enabled': True
            },
            'monthly': {
                'interval_hours': 720,  # 30 days
                'max_processing_time_seconds': 1800,  # 30 minutes
                'deep_analysis_enabled': True,
                'enabled': True
            }
        }

    def should_run_cleanup(self, phase: CleanupPhase) -> bool:
        """Check if a cleanup phase should run based on intervals."""
        if not self.config.get(phase.value, {}).get('enabled', True):
            return False

        current_time = time.time()
        last_run = self.last_cleanup.get(phase, 0)
        interval_seconds = self.config[phase.value]['interval_hours'] * 3600

        return (current_time - last_run) >= interval_seconds

    def run_scheduled_cleanup(self) -> Dict[str, Any]:
        """Run all scheduled cleanup phases that are due."""
        results = {
            'total_processing_time': 0.0,
            'phases_executed': [],
            'total_documents_processed': 0,
            'total_documents_removed': 0,
            'success': True,
            'errors': []
        }

        start_time = time.time()

        # Check and run each phase
        for phase in CleanupPhase:
            if self.should_run_cleanup(phase):
                try:
                    phase_result = self._run_cleanup_phase(phase)
                    results['phases_executed'].append({
                        'phase': phase.value,
                        'result': phase_result
                    })
                    results['total_documents_processed'] += phase_result.get('documents_processed', 0)
                    results['total_documents_removed'] += phase_result.get('documents_removed', 0)

                    # Update last cleanup time
                    self.last_cleanup[phase] = time.time()

                except Exception as e:
                    error_msg = f"Phase {phase.value} failed: {str(e)}"
                    logging.error(error_msg)
                    results['errors'].append(error_msg)
                    results['success'] = False

        results['total_processing_time'] = time.time() - start_time

        # Save cleanup history
        self._save_cleanup_history()

        return results

    def _run_cleanup_phase(self, phase: CleanupPhase) -> Dict[str, Any]:
        """Execute a specific cleanup phase."""
        phase_config = self.config[phase.value]
        max_time = phase_config.get('max_processing_time_seconds', 300)

        start_time = time.time()
        result = {
            'phase': phase.value,
            'documents_processed': 0,
            'documents_removed': 0,
            'processing_time': 0.0,
            'success': True,
            'message': ''
        }

        try:
            if phase == CleanupPhase.DAILY:
                result = self._run_daily_cleanup(max_time)
            elif phase == CleanupPhase.WEEKLY:
                result = self._run_weekly_cleanup(max_time)
            elif phase == CleanupPhase.MONTHLY:
                result = self._run_monthly_cleanup(max_time)

            result['processing_time'] = time.time() - start_time
            logging.info(f"Completed {phase.value} cleanup: {result['message']}")

        except Exception as e:
            result['success'] = False
            result['message'] = f"Failed: {str(e)}"
            result['processing_time'] = time.time() - start_time
            logging.error(f"Cleanup phase {phase.value} failed: {e}")

        return result

    def _run_daily_cleanup(self, max_time_seconds: float) -> Dict[str, Any]:
        """Daily cleanup: Quick exact duplicate removal."""
        if not hasattr(self.memory_system, 'deduplicator') or not self.memory_system.deduplicator.enabled:
            return {
                'documents_processed': 0,
                'documents_removed': 0,
                'message': 'Deduplication system not available'
            }

        # Focus on short-term memory for daily cleanup
        collection = self.memory_system.short_term_memory
        threshold = self.config['daily']['duplicate_threshold']

        # Run exact deduplication with time limit
        result = self.memory_system.deduplicator.deduplicate_collection(
            collection,
            dry_run=False,
            max_processing_time=max_time_seconds,
            similarity_threshold=threshold
        )

        return {
            'documents_processed': result.get('documents_processed', 0),
            'documents_removed': result.get('merged_documents', 0),
            'message': f"Daily cleanup removed {result.get('merged_documents', 0)} exact duplicates"
        }

    def _run_weekly_cleanup(self, max_time_seconds: float) -> Dict[str, Any]:
        """Weekly cleanup: Similarity-based clustering cleanup."""
        if not hasattr(self.memory_system, 'deduplicator') or not self.memory_system.deduplicator.enabled:
            return {
                'documents_processed': 0,
                'documents_removed': 0,
                'message': 'Deduplication system not available'
            }

        # Process both short-term and long-term memory
        total_processed = 0
        total_removed = 0

        collections = [
            ('short_term', self.memory_system.short_term_memory),
            ('long_term', self.memory_system.long_term_memory)
        ]

        threshold = self.config['weekly']['similarity_threshold']
        time_per_collection = max_time_seconds / len(collections)

        for collection_name, collection in collections:
            try:
                # Run similarity clustering with time limit
                result = self.memory_system.deduplicator.deduplicate_collection(
                    collection,
                    dry_run=False,
                    max_processing_time=time_per_collection,
                    similarity_threshold=threshold
                )

                total_processed += result.get('documents_processed', 0)
                total_removed += result.get('merged_documents', 0)

            except Exception as e:
                logging.warning(f"Weekly cleanup failed for {collection_name}: {e}")

        return {
            'documents_processed': total_processed,
            'documents_removed': total_removed,
            'message': f"Weekly cleanup processed {total_processed} documents, removed {total_removed} similar items"
        }

    def _run_monthly_cleanup(self, max_time_seconds: float) -> Dict[str, Any]:
        """Monthly cleanup: Deep analysis and optimization."""
        total_processed = 0
        total_removed = 0

        # Phase 1: Comprehensive deduplication across all collections
        if hasattr(self.memory_system, 'deduplicator') and self.memory_system.deduplicator.enabled:
            collections = [
                ('short_term', self.memory_system.short_term_memory),
                ('long_term', self.memory_system.long_term_memory)
            ]

            time_per_phase = max_time_seconds / 3  # Divide time between 3 phases

            for collection_name, collection in collections:
                try:
                    # Deep deduplication with lower threshold
                    result = self.memory_system.deduplicator.deduplicate_collection(
                        collection,
                        dry_run=False,
                        max_processing_time=time_per_phase / len(collections),
                        similarity_threshold=0.65  # Lower threshold for monthly deep clean
                    )

                    total_processed += result.get('documents_processed', 0)
                    total_removed += result.get('merged_documents', 0)

                except Exception as e:
                    logging.warning(f"Monthly deduplication failed for {collection_name}: {e}")

        # Phase 2: Advanced cleanup using similarity clustering (already implemented in maintenance)
        try:
            # Trigger enhanced maintenance
            self.memory_system._maintain_short_term_memory()

        except Exception as e:
            logging.warning(f"Monthly enhanced maintenance failed: {e}")

        # Phase 3: Analytics and optimization recommendations
        optimization_insights = self._generate_optimization_insights()

        return {
            'documents_processed': total_processed,
            'documents_removed': total_removed,
            'message': (
                f"Monthly deep cleanup processed {total_processed} documents, "
                f"insights: {len(optimization_insights)} recommendations"
            ),
            'optimization_insights': optimization_insights
        }

    def _generate_optimization_insights(self) -> list:
        """Generate optimization recommendations based on system analysis."""
        insights = []

        try:
            # Get collection statistics
            stats = self.memory_system.get_collection_stats()

            # Check for imbalanced collections
            short_term_count = stats.get('collections', {}).get('short_term', {}).get('count', 0)
            long_term_count = stats.get('collections', {}).get('long_term', {}).get('count', 0)

            if short_term_count > long_term_count * 2:
                insights.append({
                    'type': 'collection_imbalance',
                    'message': 'Short-term memory is significantly larger than long-term',
                    'recommendation': 'Consider adjusting importance thresholds or cleanup intervals'
                })

            # Check deduplication effectiveness
            if hasattr(self.memory_system, 'deduplicator'):
                dedup_stats = self.memory_system.deduplicator.get_deduplication_stats()
                effectiveness = dedup_stats.get('deduplication_efficiency', 0)

                if effectiveness < 10:
                    insights.append({
                        'type': 'low_deduplication',
                        'message': f'Low deduplication effectiveness: {effectiveness}%',
                        'recommendation': 'Consider adjusting similarity thresholds or embedding model'
                    })

            # Memory size recommendations
            total_documents = short_term_count + long_term_count
            if total_documents > 10000:
                insights.append({
                    'type': 'large_memory',
                    'message': f'Large memory size: {total_documents} documents',
                    'recommendation': 'Consider implementing permanent storage tier or more aggressive cleanup'
                })

        except Exception as e:
            logging.warning(f"Failed to generate optimization insights: {e}")

        return insights

    def _load_cleanup_history(self):
        """Load cleanup history from persistent storage."""
        try:
            # Implementation would load from file or database
            # For now, initialize with current time minus intervals to prevent immediate cleanup
            current_time = time.time()
            self.last_cleanup = {
                CleanupPhase.DAILY: current_time - (22 * 3600),  # 22 hours ago
                CleanupPhase.WEEKLY: current_time - (166 * 3600),  # 166 hours ago
                CleanupPhase.MONTHLY: current_time - (718 * 3600)  # 718 hours ago
            }
        except Exception as e:
            logging.warning(f"Failed to load cleanup history: {e}")

    def _save_cleanup_history(self):
        """Save cleanup history to persistent storage."""
        try:
            # Implementation would save to file or database
            # For now, just log the save attempt
            logging.debug("Cleanup history saved (placeholder implementation)")
        except Exception as e:
            logging.warning(f"Failed to save cleanup history: {e}")

    def get_cleanup_status(self) -> Dict[str, Any]:
        """Get status of all cleanup phases."""
        current_time = time.time()
        status = {
            'current_time': current_time,
            'phases': {}
        }

        for phase in CleanupPhase:
            config = self.config.get(phase.value, {})
            last_run = self.last_cleanup.get(phase, 0)
            interval_seconds = config.get('interval_hours', 24) * 3600

            next_run = last_run + interval_seconds
            time_until_next = max(0, next_run - current_time)

            status['phases'][phase.value] = {
                'enabled': config.get('enabled', True),
                'last_run': last_run,
                'next_run': next_run,
                'time_until_next_hours': time_until_next / 3600,
                'is_due': time_until_next == 0,
                'interval_hours': config.get('interval_hours', 24)
            }

        return status
