import time
import asyncio
import random
import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import threading

from .hierarchical import HierarchicalMemorySystem
from .scorer import MemoryImportanceScorer
from .progressive_cleanup import ProgressiveCleanupManager


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
        
        # Thread safety
        self._maintenance_lock = threading.RLock()
        self._state_lock = threading.RLock()
        
        # Initialize sub-managers
        self.ttl_manager = TTLManager(lifecycle_config.get('ttl', {}))
        self.aging = MemoryAging(lifecycle_config.get('aging', {}))
        self.progressive_cleanup = ProgressiveCleanupManager(
            memory_system, 
            lifecycle_config.get('progressive_cleanup', {})
        )
        
        # Maintenance configuration
        self.maintenance_config = lifecycle_config.get('maintenance', {})
        self.maintenance_enabled = self.maintenance_config.get('enabled', True)
        
        # Background thread for maintenance
        self._maintenance_thread = None
        self._stop_event = threading.Event()  # Use Event for graceful shutdown
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
    
    async def cleanup_expired_documents(self, collection_name: str = None) -> Dict[str, Any]:
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
                
                # Get all documents with IDs to check for expiry
                all_data = await asyncio.to_thread(collection.get)
                total_docs = len(all_data.get('ids', []))
                
                expired_doc_ids = []
                if all_data.get('ids') and all_data.get('metadatas'):
                    for doc_id, metadata in zip(all_data['ids'], all_data['metadatas']):
                        if metadata and self.ttl_manager.should_expire(metadata):
                            expired_doc_ids.append(doc_id)
                
                # Actually delete expired documents
                cleanup_performed = False
                if expired_doc_ids:
                    try:
                        await asyncio.to_thread(collection.delete, ids=expired_doc_ids)
                        cleanup_performed = True
                        logging.info(f"Deleted {len(expired_doc_ids)} expired documents from {coll_name}")
                    except Exception as delete_error:
                        error_msg = f"Failed to delete expired documents from {coll_name}: {delete_error}"
                        results['errors'].append(error_msg)
                        logging.error(error_msg)
                
                results['cleaned_collections'].append({
                    'collection': coll_name,
                    'total_docs': total_docs,
                    'expired_docs': len(expired_doc_ids),
                    'cleanup_performed': cleanup_performed,
                    'deleted_doc_ids': expired_doc_ids if cleanup_performed else []
                })
                
                results['total_expired'] += len(expired_doc_ids)
                results['total_checked'] += total_docs
                
                logging.info(f"Cleanup check for {coll_name}: {len(expired_doc_ids)}/{total_docs} expired")
                
            except Exception as e:
                error_msg = f"Error cleaning {coll_name}: {str(e)}"
                results['errors'].append(error_msg)
                logging.error(error_msg)
        
        return results
    
    async def refresh_aging_scores(self, collection_name: str = None, sample_size: int = 100) -> Dict[str, Any]:
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
                docs = await asyncio.to_thread(collection.similarity_search, "", k=sample_size)
                
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
        with self._state_lock:
            if not self.maintenance_enabled:
                logging.info("Background maintenance disabled")
                return
            
            if self._maintenance_thread and self._maintenance_thread.is_alive():
                logging.warning("Background maintenance already running")
                return
            
            self._stop_event.clear()
            
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
        with self._state_lock:
            self._stop_event.set()  # Signal the thread to stop
            if self._maintenance_thread and self._maintenance_thread.is_alive():
                logging.info("Stopping background maintenance thread...")
                self._maintenance_thread.join(timeout=10)  # Increased timeout
                if self._maintenance_thread.is_alive():
                    logging.warning("Background maintenance thread did not stop gracefully within timeout")
                else:
                    logging.info("Background maintenance thread stopped successfully")
            else:
                logging.info("Background maintenance thread was not running")
            
            # Clear the thread reference
            self._maintenance_thread = None
    
    def _maintenance_loop(self):
        """Main maintenance loop running in background thread."""
        logging.info("Background maintenance loop started")
        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # Use lock for maintenance operations to prevent conflicts
                with self._maintenance_lock:
                    if self._stop_event.is_set(): break
                    
                    # Check if it's time for cleanup (every hour)
                    if current_time - self._last_cleanup >= 3600:  # 1 hour
                        self._scheduled_cleanup()
                        self._last_cleanup = current_time
                    
                    if self._stop_event.is_set(): break
                    
                    # Check if it's time for statistics (every 6 hours)
                    if current_time - self._last_statistics >= 21600:  # 6 hours
                        self._scheduled_statistics()
                        self._last_statistics = current_time
                    
                    if self._stop_event.is_set(): break
                    
                    # Check if it's time for aging refresh (every 24 hours)
                    if current_time - self._last_aging_refresh >= 86400:  # 24 hours
                        self._scheduled_aging_refresh()
                        self._last_aging_refresh = current_time
                    
                    if self._stop_event.is_set(): break
                    
                    # Check if it's time for deep maintenance (every week)
                    if current_time - self._last_deep_maintenance >= 604800:  # 1 week
                        self._scheduled_deep_maintenance()
                        self._last_deep_maintenance = current_time
                
                # Wait for the next check, or until stop is signaled
                # This is an interruptible sleep.
                self._stop_event.wait(timeout=300)  # Wait for 5 minutes
                
            except Exception as e:
                logging.error(f"Maintenance loop error: {e}")
                # Wait before retrying on error, but still be interruptible
                if not self._stop_event.is_set():
                    self._stop_event.wait(timeout=300)
        
        logging.info("Background maintenance loop exited")
    
    def _scheduled_cleanup(self):
        """Scheduled cleanup task."""
        logging.info("Running scheduled cleanup")
        try:
            # Run async cleanup in thread-safe way
            import asyncio
            if hasattr(asyncio, 'run'):
                results = asyncio.run(self.cleanup_expired_documents())
            else:
                # Fallback for older Python versions
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    results = loop.run_until_complete(self.cleanup_expired_documents())
                finally:
                    loop.close()
            logging.info(f"Cleanup results: {results['total_expired']} expired out of {results['total_checked']}")
        except Exception as e:
            logging.error(f"Error during scheduled cleanup: {e}")
    
    def _scheduled_statistics(self):
        """Scheduled statistics task."""
        logging.info("Running scheduled statistics collection")
        stats = self.memory_system.get_collection_stats()
        logging.info(f"Collection stats: {stats}")
    
    def _scheduled_aging_refresh(self):
        """Scheduled aging refresh task."""
        logging.info("Running scheduled aging refresh")
        try:
            # Run async aging refresh in thread-safe way
            import asyncio
            if hasattr(asyncio, 'run'):
                results = asyncio.run(self.refresh_aging_scores())
            else:
                # Fallback for older Python versions
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    results = loop.run_until_complete(self.refresh_aging_scores())
                finally:
                    loop.close()
            logging.info(f"Aging refresh: {results['total_refreshed']} scores refreshed")
        except Exception as e:
            logging.error(f"Error during aging refresh: {e}")
    
    def _scheduled_deep_maintenance(self):
        """Scheduled deep maintenance task."""
        logging.info("Running scheduled deep maintenance")
        
        # Phase 1: Traditional cleanup + aging refresh
        try:
            import asyncio
            if hasattr(asyncio, 'run'):
                cleanup = asyncio.run(self.cleanup_expired_documents())
                aging = asyncio.run(self.refresh_aging_scores())
            else:
                # Fallback for older Python versions
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    cleanup = loop.run_until_complete(self.cleanup_expired_documents())
                    aging = loop.run_until_complete(self.refresh_aging_scores())
                finally:
                    loop.close()
        except Exception as e:
            logging.error(f"Error during deep maintenance async operations: {e}")
            cleanup = {'total_expired': 0, 'total_checked': 0}
            aging = {'total_refreshed': 0}
        
        # Phase 2: Progressive cleanup (daily/weekly/monthly phases)
        progressive_result = self.progressive_cleanup.run_scheduled_cleanup()
        
        # Phase 3: Statistics collection
        stats = self.memory_system.get_collection_stats()
        
        logging.info(f"Deep maintenance complete: "
                    f"expired {cleanup['total_expired']}, "
                    f"refreshed {aging['total_refreshed']}, "
                    f"progressive cleanup: {progressive_result.get('total_documents_removed', 0)} removed, "
                    f"phases executed: {len(progressive_result.get('phases_executed', []))}, "
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
                'thread_active': bool(self._maintenance_thread and self._maintenance_thread.is_alive()),
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
        
        # Add progressive cleanup status
        stats['progressive_cleanup'] = self.progressive_cleanup.get_cleanup_status()
        
        return stats