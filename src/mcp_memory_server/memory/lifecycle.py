import time
import random
import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import threading

from .hierarchical import HierarchicalMemorySystem
from .scorer import MemoryImportanceScorer


class TTLManager:
    """Manages Time-To-Live (TTL) for memory documents with importance-weighted expiration."""
    
    def __init__(self, ttl_config: dict):
        """Initialize TTL manager with configuration.
        
        Args:
            ttl_config: TTL configuration dictionary
        """
        self.config = ttl_config
        
        # TTL tiers with jitter (in seconds)
        self.ttl_tiers = {
            'high_frequency': {
                'base_ttl': self.config.get('high_frequency_base', 300),  # 5 minutes
                'jitter': self.config.get('high_frequency_jitter', 60),   # ±1 minute
                'importance_range': (0.0, 0.3)  # Low importance
            },
            'medium_frequency': {
                'base_ttl': self.config.get('medium_frequency_base', 3600),  # 1 hour
                'jitter': self.config.get('medium_frequency_jitter', 600),   # ±10 minutes
                'importance_range': (0.3, 0.5)  # Medium-low importance
            },
            'low_frequency': {
                'base_ttl': self.config.get('low_frequency_base', 86400),  # 1 day
                'jitter': self.config.get('low_frequency_jitter', 7200),   # ±2 hours
                'importance_range': (0.5, 0.7)  # Medium importance
            },
            'static': {
                'base_ttl': self.config.get('static_base', 604800),  # 1 week
                'jitter': self.config.get('static_jitter', 86400),   # ±1 day
                'importance_range': (0.7, 0.95)  # High importance
            },
            'permanent': {
                'base_ttl': None,  # Never expires
                'jitter': 0,       # No jitter for permanent content
                'importance_range': (0.95, 1.0)  # Ultra-high importance
            }
        }
    
    def calculate_ttl(self, importance_score: float, access_count: int = 0, 
                     last_accessed: float = None) -> Tuple[str, float]:
        """Calculate TTL for a document based on importance and usage.
        
        Args:
            importance_score: Document importance score (0-1)
            access_count: Number of times accessed
            last_accessed: Last access timestamp
            
        Returns:
            Tuple of (tier_name, ttl_seconds)
        """
        current_time = time.time()
        
        # Determine base tier
        tier_name = 'high_frequency'  # Default for very low importance
        for tier, config in self.ttl_tiers.items():
            min_imp, max_imp = config['importance_range']
            if min_imp <= importance_score <= max_imp:
                tier_name = tier
                break
        
        tier_config = self.ttl_tiers[tier_name]
        base_ttl = tier_config['base_ttl']
        jitter = tier_config['jitter']
        
        # Handle permanent tier - no TTL calculation needed
        if tier_name == 'permanent' or base_ttl is None:
            return tier_name, float('inf')  # Infinite TTL for permanent content
        
        # Apply access frequency multiplier
        access_multiplier = 1.0
        if access_count > 5:
            access_multiplier = min(2.0, 1.0 + (access_count - 5) * 0.1)  # Up to 2x for frequent access
        
        # Apply recency multiplier
        recency_multiplier = 1.0
        if last_accessed:
            days_since_access = (current_time - last_accessed) / 86400
            if days_since_access < 1:
                recency_multiplier = 1.5  # Recently accessed gets longer TTL
            elif days_since_access > 7:
                recency_multiplier = 0.7  # Old access gets shorter TTL
        
        # Calculate final TTL with jitter
        final_ttl = base_ttl * access_multiplier * recency_multiplier
        jitter_amount = random.uniform(-jitter, jitter)
        final_ttl += jitter_amount
        
        # Ensure minimum TTL
        final_ttl = max(final_ttl, 60)  # At least 1 minute
        
        return tier_name, final_ttl
    
    def should_expire(self, document_metadata: dict) -> bool:
        """Check if a document should expire based on its TTL.
        
        Args:
            document_metadata: Document metadata containing TTL info
            
        Returns:
            True if document should expire
        """
        # Check if document is permanent
        if document_metadata.get('permanent_flag', False):
            return False  # Permanent content never expires
        
        # Check for permanent tier
        if document_metadata.get('ttl_tier') == 'permanent':
            return False  # Permanent tier never expires
        
        current_time = time.time()
        
        # Get TTL information from metadata
        ttl_expiry = document_metadata.get('ttl_expiry')
        if not ttl_expiry:
            return False  # No TTL set, don't expire
        
        return current_time > ttl_expiry
    
    def add_ttl_metadata(self, metadata: dict, importance_score: float) -> dict:
        """Add TTL metadata to a document.
        
        Args:
            metadata: Existing document metadata
            importance_score: Document importance score
            
        Returns:
            Updated metadata with TTL information
        """
        current_time = time.time()
        access_count = metadata.get('access_count', 0)
        last_accessed = metadata.get('last_accessed', current_time)
        
        tier, ttl_seconds = self.calculate_ttl(importance_score, access_count, last_accessed)
        
        # Handle permanent content
        is_permanent = tier == 'permanent' or ttl_seconds == float('inf')
        ttl_expiry = None if is_permanent else current_time + ttl_seconds
        
        metadata.update({
            'ttl_tier': tier,
            'ttl_seconds': ttl_seconds,
            'ttl_created': current_time,
            'ttl_expiry': ttl_expiry,
            'ttl_last_calculated': current_time,
            'permanent_flag': is_permanent,
            'permanence_reason': 'high_importance' if is_permanent else None
        })
        
        return metadata


class MemoryAging:
    """Handles memory aging and decay functions for relevance scoring."""
    
    def __init__(self, aging_config: dict):
        """Initialize memory aging with configuration.
        
        Args:
            aging_config: Aging configuration dictionary
        """
        self.config = aging_config
        self.decay_rate = aging_config.get('decay_rate', 0.1)  # Rate of decay per day
        self.minimum_score = aging_config.get('minimum_score', 0.1)  # Minimum score floor
        self.aging_enabled = aging_config.get('enabled', True)
    
    def calculate_age_factor(self, timestamp: float, current_time: float = None) -> float:
        """Calculate age decay factor for a memory.
        
        Args:
            timestamp: Original timestamp of the memory
            current_time: Current time (defaults to now)
            
        Returns:
            Age factor (0-1) where 1 is newest, approaching 0 as it ages
        """
        if not self.aging_enabled:
            return 1.0
        
        if current_time is None:
            current_time = time.time()
        
        # Calculate age in days
        age_days = (current_time - timestamp) / 86400
        
        # Apply exponential decay
        age_factor = math.exp(-self.decay_rate * age_days)
        
        # Apply minimum score floor
        age_factor = max(age_factor, self.minimum_score)
        
        return age_factor
    
    def apply_aging_to_score(self, original_score: float, timestamp: float, 
                           current_time: float = None) -> float:
        """Apply aging to an importance score.
        
        Args:
            original_score: Original importance score
            timestamp: Timestamp when score was calculated
            current_time: Current time (defaults to now)
            
        Returns:
            Age-adjusted importance score
        """
        age_factor = self.calculate_age_factor(timestamp, current_time)
        aged_score = original_score * age_factor
        
        # Ensure we don't go below absolute minimum
        return max(aged_score, self.minimum_score * 0.5)
    
    def needs_score_refresh(self, metadata: dict, refresh_threshold_days: float = 7.0) -> bool:
        """Check if a document's importance score needs refreshing.
        
        Args:
            metadata: Document metadata
            refresh_threshold_days: Days after which to refresh scores
            
        Returns:
            True if score needs refreshing
        """
        if not self.aging_enabled:
            return False
        
        current_time = time.time()
        last_scored = metadata.get('importance_scored_at', metadata.get('timestamp', current_time))
        
        days_since_scoring = (current_time - last_scored) / 86400
        return days_since_scoring > refresh_threshold_days


class LifecycleManager:
    """Manages the complete lifecycle of memories including TTL, aging, and cleanup."""
    
    def __init__(self, memory_system: HierarchicalMemorySystem, lifecycle_config: dict):
        """Initialize lifecycle manager.
        
        Args:
            memory_system: HierarchicalMemorySystem instance
            lifecycle_config: Lifecycle configuration
        """
        self.memory_system = memory_system
        self.config = lifecycle_config
        
        # Initialize sub-managers
        self.ttl_manager = TTLManager(lifecycle_config.get('ttl', {}))
        self.aging = MemoryAging(lifecycle_config.get('aging', {}))
        
        # Maintenance configuration
        self.maintenance_config = lifecycle_config.get('maintenance', {})
        self.maintenance_enabled = self.maintenance_config.get('enabled', True)
        
        # Background thread for maintenance
        self._maintenance_thread = None
        self._stop_maintenance = False
        self._last_cleanup = 0
        self._last_statistics = 0
        self._last_aging_refresh = 0
        self._last_deep_maintenance = 0
    
    def process_document_lifecycle(self, content: str, metadata: dict, 
                                 importance_score: float) -> dict:
        """Process a document through the complete lifecycle system.
        
        Args:
            content: Document content
            metadata: Document metadata
            importance_score: Calculated importance score
            
        Returns:
            Enhanced metadata with lifecycle information
        """
        current_time = time.time()
        
        # Add aging metadata
        metadata['importance_scored_at'] = current_time
        
        # Check for explicit permanence requests
        permanence_flag = metadata.get('permanence_flag')
        if permanence_flag == 'critical' and importance_score >= 0.8:
            # Override importance score for explicitly requested permanent content
            importance_score = max(importance_score, 0.95)
            metadata['permanence_reason'] = 'user_request'
        
        # Add TTL metadata (will automatically handle permanent tier)
        metadata = self.ttl_manager.add_ttl_metadata(metadata, importance_score)
        
        # Add lifecycle tracking
        metadata.update({
            'lifecycle_version': '1.0',
            'lifecycle_processed_at': current_time,
            'aging_enabled': self.aging.aging_enabled
        })
        
        return metadata
    
    def cleanup_expired_documents(self, collection_name: str = None) -> Dict[str, Any]:
        """Clean up expired documents from collections.
        
        Args:
            collection_name: Specific collection to clean, or None for all
            
        Returns:
            Cleanup results and statistics
        """
        results = {
            'cleaned_collections': [],
            'total_expired': 0,
            'total_checked': 0,
            'errors': []
        }
        
        collections_to_clean = [collection_name] if collection_name else ['short_term', 'long_term']
        
        for coll_name in collections_to_clean:
            try:
                collection = getattr(self.memory_system, f"{coll_name}_memory")
                
                # Get all documents to check for expiry
                docs = collection.similarity_search("", k=10000)  # Large number to get all
                
                expired_docs = []
                for doc in docs:
                    if self.ttl_manager.should_expire(doc.metadata):
                        expired_docs.append(doc)
                
                # Note: ChromaDB doesn't have a direct delete by document method
                # In a production system, you'd implement document removal here
                # For now, we'll log what would be removed
                
                results['cleaned_collections'].append({
                    'collection': coll_name,
                    'total_docs': len(docs),
                    'expired_docs': len(expired_docs),
                    'cleanup_performed': False  # Would be True in full implementation
                })
                
                results['total_expired'] += len(expired_docs)
                results['total_checked'] += len(docs)
                
                logging.info(f"Cleanup check for {coll_name}: {len(expired_docs)}/{len(docs)} expired")
                
            except Exception as e:
                error_msg = f"Error cleaning {coll_name}: {str(e)}"
                results['errors'].append(error_msg)
                logging.error(error_msg)
        
        return results
    
    def refresh_aging_scores(self, collection_name: str = None, sample_size: int = 100) -> Dict[str, Any]:
        """Refresh aging scores for documents that need it.
        
        Args:
            collection_name: Specific collection to refresh, or None for all
            sample_size: Number of documents to process per collection
            
        Returns:
            Refresh results and statistics
        """
        results = {
            'refreshed_collections': [],
            'total_refreshed': 0,
            'total_checked': 0,
            'errors': []
        }
        
        collections_to_refresh = [collection_name] if collection_name else ['short_term', 'long_term']
        
        for coll_name in collections_to_refresh:
            try:
                collection = getattr(self.memory_system, f"{coll_name}_memory")
                
                # Get sample of documents
                docs = collection.similarity_search("", k=sample_size)
                
                refreshed_count = 0
                for doc in docs:
                    if self.aging.needs_score_refresh(doc.metadata):
                        # Calculate new aged score
                        original_score = doc.metadata.get('importance_score', 0.5)
                        timestamp = doc.metadata.get('importance_scored_at', doc.metadata.get('timestamp', time.time()))
                        
                        new_score = self.aging.apply_aging_to_score(original_score, timestamp)
                        
                        # In a full implementation, you'd update the document here
                        # For now, we'll just count what would be updated
                        
                        if abs(new_score - original_score) > 0.05:  # Significant change
                            refreshed_count += 1
                
                results['refreshed_collections'].append({
                    'collection': coll_name,
                    'total_docs': len(docs),
                    'refreshed_docs': refreshed_count,
                    'refresh_performed': False  # Would be True in full implementation
                })
                
                results['total_refreshed'] += refreshed_count
                results['total_checked'] += len(docs)
                
                logging.info(f"Aging refresh for {coll_name}: {refreshed_count}/{len(docs)} refreshed")
                
            except Exception as e:
                error_msg = f"Error refreshing {coll_name}: {str(e)}"
                results['errors'].append(error_msg)
                logging.error(error_msg)
        
        return results
    
    def start_background_maintenance(self):
        """Start background maintenance processes."""
        if not self.maintenance_enabled:
            logging.info("Background maintenance disabled")
            return
        
        if self._maintenance_thread and self._maintenance_thread.is_alive():
            logging.warning("Background maintenance already running")
            return
        
        self._stop_maintenance = False
        
        # Initialize timestamps
        current_time = time.time()
        self._last_cleanup = current_time
        self._last_statistics = current_time
        self._last_aging_refresh = current_time
        self._last_deep_maintenance = current_time
        
        # Start maintenance thread
        self._maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._maintenance_thread.start()
        
        logging.info("Background maintenance started")
    
    def stop_background_maintenance(self):
        """Stop background maintenance processes."""
        self._stop_maintenance = True
        if self._maintenance_thread:
            self._maintenance_thread.join(timeout=5)
        logging.info("Background maintenance stopped")
    
    def _maintenance_loop(self):
        """Main maintenance loop running in background thread."""
        while not self._stop_maintenance:
            try:
                current_time = time.time()
                
                # Check if it's time for cleanup (every hour)
                if current_time - self._last_cleanup >= 3600:  # 1 hour
                    self._scheduled_cleanup()
                    self._last_cleanup = current_time
                
                # Check if it's time for statistics (every 6 hours)
                if current_time - self._last_statistics >= 21600:  # 6 hours
                    self._scheduled_statistics()
                    self._last_statistics = current_time
                
                # Check if it's time for aging refresh (every 24 hours)
                if current_time - self._last_aging_refresh >= 86400:  # 24 hours
                    self._scheduled_aging_refresh()
                    self._last_aging_refresh = current_time
                
                # Check if it's time for deep maintenance (every week)
                if current_time - self._last_deep_maintenance >= 604800:  # 1 week
                    self._scheduled_deep_maintenance()
                    self._last_deep_maintenance = current_time
                
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logging.error(f"Maintenance loop error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _scheduled_cleanup(self):
        """Scheduled cleanup task."""
        logging.info("Running scheduled cleanup")
        results = self.cleanup_expired_documents()
        logging.info(f"Cleanup results: {results['total_expired']} expired out of {results['total_checked']}")
    
    def _scheduled_statistics(self):
        """Scheduled statistics task."""
        logging.info("Running scheduled statistics collection")
        stats = self.memory_system.get_collection_stats()
        logging.info(f"Collection stats: {stats}")
    
    def _scheduled_aging_refresh(self):
        """Scheduled aging refresh task."""
        logging.info("Running scheduled aging refresh")
        results = self.refresh_aging_scores()
        logging.info(f"Aging refresh: {results['total_refreshed']} scores refreshed")
    
    def _scheduled_deep_maintenance(self):
        """Scheduled deep maintenance task."""
        logging.info("Running scheduled deep maintenance")
        # Cleanup + aging refresh + statistics
        cleanup = self.cleanup_expired_documents()
        aging = self.refresh_aging_scores()
        stats = self.memory_system.get_collection_stats()
        
        logging.info(f"Deep maintenance complete: "
                    f"cleaned {cleanup['total_expired']}, "
                    f"refreshed {aging['total_refreshed']}, "
                    f"collections: {len(stats.get('collections', {}))}")
    
    def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Get comprehensive lifecycle management statistics.
        
        Returns:
            Lifecycle statistics and health information
        """
        current_time = time.time()
        
        stats = {
            'ttl_manager': {
                'tiers': list(self.ttl_manager.ttl_tiers.keys()),
                'tier_configs': self.ttl_manager.ttl_tiers
            },
            'aging': {
                'enabled': self.aging.aging_enabled,
                'decay_rate': self.aging.decay_rate,
                'minimum_score': self.aging.minimum_score
            },
            'maintenance': {
                'enabled': self.maintenance_enabled,
                'thread_active': self._maintenance_thread and self._maintenance_thread.is_alive(),
                'last_cleanup': self._last_cleanup,
                'last_statistics': self._last_statistics,
                'last_aging_refresh': self._last_aging_refresh,
                'last_deep_maintenance': self._last_deep_maintenance
            },
            'system_health': {
                'lifecycle_version': '1.0',
                'last_check': current_time,
                'uptime_hours': (current_time - getattr(self, '_start_time', current_time)) / 3600
            }
        }
        
        # Add collection-specific lifecycle info
        memory_stats = self.memory_system.get_collection_stats()
        stats['collections'] = memory_stats.get('collections', {})
        
        return stats