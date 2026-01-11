"""
Unit tests for MemoryIntelligenceSystem (Simplified)

Tests the practical analytics features:
- System overview and health
- Storage patterns and distribution
- Deduplication effectiveness
- Query performance metrics
- Actionable optimization recommendations
"""

import pytest
import time
from unittest.mock import Mock
from src.mcp_memory_server.analytics.intelligence import MemoryIntelligenceSystem


@pytest.fixture
def mock_memory_system():
    """Create a mock memory system for testing."""
    memory_system = Mock()

    # Mock deduplicator with proper boolean enabled attribute
    memory_system.deduplicator = Mock()
    memory_system.deduplicator.enabled = True
    memory_system.deduplicator.get_deduplication_stats.return_value = {
        'total_duplicates_found': 15,
        'total_documents_merged': 12,
        'deduplication_efficiency': 25.5,
        'processing_time_total': 5.5
    }

    # Mock query monitor
    memory_system.query_monitor = Mock()

    # Mock chunk_manager
    memory_system.chunk_manager = Mock()
    memory_system.chunk_manager.get_relationship_statistics.return_value = {
        'total_relationships': 50,
        'document_count': 25
    }

    # Mock get_collection_stats method
    memory_system.get_collection_stats.return_value = {
        'collections': {
            'short_term_memory': {
                'count': 100,
                'status': 'active'
            },
            'long_term_memory': {
                'count': 50,
                'status': 'active'
            }
        },
        'total_documents': 150,
        'last_updated': time.time()
    }

    # Mock get_query_performance_stats method
    memory_system.get_query_performance_stats.return_value = {
        'query_count': 500,
        'response_time_stats': {
            'mean_ms': 150.0,
            'median_ms': 120.0,
            'p95_ms': 350.0
        }
    }

    return memory_system


@pytest.fixture
def analytics_config():
    """Sample analytics configuration."""
    return {
        'history_retention_days': 30,
        'cache_duration_minutes': 15,
    }


@pytest.fixture
def intelligence_system(mock_memory_system, analytics_config):
    """Create MemoryIntelligenceSystem instance."""
    return MemoryIntelligenceSystem(mock_memory_system, analytics_config)


class TestMemoryIntelligenceSystem:
    """Test suite for MemoryIntelligenceSystem."""

    def test_initialization_with_config(self, mock_memory_system, analytics_config):
        """Test initialization with custom configuration."""
        intelligence = MemoryIntelligenceSystem(mock_memory_system, analytics_config)

        assert intelligence.memory_system == mock_memory_system
        assert intelligence.config == analytics_config
        assert intelligence.analytics_history == []
        assert intelligence.optimization_recommendations == []
        assert isinstance(intelligence.system_start_time, float)

    def test_initialization_with_default_config(self, mock_memory_system):
        """Test initialization with default configuration."""
        intelligence = MemoryIntelligenceSystem(mock_memory_system)

        assert intelligence.config['history_retention_days'] == 30
        assert intelligence.config['cache_duration_minutes'] == 15

    def test_initialization_with_none_config(self, mock_memory_system):
        """Test initialization with None config uses defaults."""
        intelligence = MemoryIntelligenceSystem(mock_memory_system, None)

        assert isinstance(intelligence.config, dict)
        assert 'history_retention_days' in intelligence.config

    def test_system_overview_generation(self, intelligence_system):
        """Test generation of system overview."""
        overview = intelligence_system._generate_system_overview()

        # Check required fields
        assert 'total_documents' in overview
        assert 'active_collections' in overview
        assert 'uptime_hours' in overview
        assert 'deduplication_enabled' in overview
        assert 'storage_efficiency' in overview
        assert 'query_monitoring_active' in overview
        assert 'relationship_tracking_active' in overview
        assert 'estimated_storage_mb' in overview
        assert 'system_maturity' in overview

        # Check values are reasonable
        assert overview['total_documents'] == 150
        assert overview['active_collections'] == 2
        assert overview['deduplication_enabled'] is True
        assert overview['query_monitoring_active'] is True
        assert overview['relationship_tracking_active'] is True

    def test_comprehensive_analytics_generation(self, intelligence_system):
        """Test generation of comprehensive analytics."""
        analytics = intelligence_system.generate_comprehensive_analytics()

        # Check main sections exist
        assert 'timestamp' in analytics
        assert 'system_overview' in analytics
        assert 'storage_analytics' in analytics
        assert 'deduplication_intelligence' in analytics
        assert 'query_performance_insights' in analytics
        assert 'optimization_recommendations' in analytics
        assert 'system_health_assessment' in analytics

        # Check deprecated features return proper status
        assert analytics['predictive_analytics']['status'] == 'not_implemented'
        assert analytics['trend_analysis']['status'] == 'not_implemented'
        assert analytics['cost_benefit_analysis']['status'] == 'not_implemented'

    def test_storage_patterns_analysis(self, intelligence_system):
        """Test analysis of storage patterns."""
        storage_analysis = intelligence_system._analyze_storage_patterns()

        assert 'total_documents' in storage_analysis
        assert 'collection_distribution' in storage_analysis
        assert 'recommendations' in storage_analysis

        assert storage_analysis['total_documents'] == 150
        assert isinstance(storage_analysis['collection_distribution'], dict)
        assert isinstance(storage_analysis['recommendations'], list)

    def test_storage_patterns_with_distribution(self, intelligence_system):
        """Test storage patterns include correct distribution."""
        storage_analysis = intelligence_system._analyze_storage_patterns()

        distribution = storage_analysis['collection_distribution']

        # Check short_term_memory distribution
        assert 'short_term_memory' in distribution
        assert distribution['short_term_memory']['document_count'] == 100
        assert distribution['short_term_memory']['percentage'] == pytest.approx(66.67, rel=0.01)

        # Check long_term_memory distribution
        assert 'long_term_memory' in distribution
        assert distribution['long_term_memory']['document_count'] == 50
        assert distribution['long_term_memory']['percentage'] == pytest.approx(33.33, rel=0.01)

    def test_deduplication_effectiveness_analysis(self, intelligence_system):
        """Test analysis of deduplication effectiveness."""
        dedup_analysis = intelligence_system._analyze_deduplication_effectiveness()

        assert dedup_analysis['enabled'] is True
        assert 'current_stats' in dedup_analysis
        assert 'relationship_stats' in dedup_analysis

        # Check current stats from mock
        assert dedup_analysis['current_stats']['total_duplicates_found'] == 15
        assert dedup_analysis['current_stats']['deduplication_efficiency'] == 25.5

    def test_deduplication_disabled(self, mock_memory_system):
        """Test deduplication analysis when disabled."""
        mock_memory_system.deduplicator.enabled = False
        intelligence = MemoryIntelligenceSystem(mock_memory_system)

        dedup_analysis = intelligence._analyze_deduplication_effectiveness()

        assert dedup_analysis['enabled'] is False
        assert 'message' in dedup_analysis

    def test_query_patterns_analysis(self, intelligence_system):
        """Test analysis of query patterns."""
        query_analysis = intelligence_system._analyze_query_patterns()

        assert query_analysis['enabled'] is True
        assert 'daily_performance' in query_analysis
        assert 'weekly_performance' in query_analysis

    def test_query_patterns_without_monitor(self, mock_memory_system):
        """Test query patterns when monitor not available."""
        del mock_memory_system.query_monitor
        intelligence = MemoryIntelligenceSystem(mock_memory_system)

        query_analysis = intelligence._analyze_query_patterns()

        assert query_analysis['enabled'] is False
        assert 'message' in query_analysis

    def test_optimization_recommendations_generation(self, intelligence_system):
        """Test generation of optimization recommendations."""
        recommendations = intelligence_system._generate_optimization_recommendations()

        assert isinstance(recommendations, list)

        # Each recommendation should have required fields
        for rec in recommendations:
            assert 'priority' in rec
            assert 'category' in rec
            assert 'title' in rec
            assert 'description' in rec
            assert 'action' in rec
            assert 'id' in rec
            assert 'generated_at' in rec

    def test_optimization_recommendations_for_large_collection(self, mock_memory_system):
        """Test recommendations for large document collection."""
        # Set up large collection with low efficiency
        mock_memory_system.get_collection_stats.return_value = {
            'collections': {
                'short_term_memory': {'count': 800, 'status': 'active'},
                'long_term_memory': {'count': 200, 'status': 'active'}
            }
        }
        mock_memory_system.deduplicator.enabled = False

        intelligence = MemoryIntelligenceSystem(mock_memory_system)
        recommendations = intelligence._generate_optimization_recommendations()

        # Should recommend enabling deduplication
        dedup_rec = [r for r in recommendations if 'Deduplication' in r.get('title', '')]
        assert len(dedup_rec) > 0

    def test_system_health_assessment(self, intelligence_system):
        """Test system health assessment."""
        health = intelligence_system._assess_system_health()

        assert 'overall_score' in health
        assert 'status' in health
        assert 'health_factors' in health

        # Score should be between 0 and 1
        assert 0 <= health['overall_score'] <= 1

        # Status should be valid
        assert health['status'] in ['excellent', 'good', 'fair', 'needs_attention']

    def test_system_health_factors(self, intelligence_system):
        """Test that health factors are calculated correctly."""
        health = intelligence_system._assess_system_health()

        health_factors = health['health_factors']

        # Storage health should be present
        assert 'storage' in health_factors
        assert 'score' in health_factors['storage']

        # Performance health should be present (query_monitor exists)
        assert 'performance' in health_factors
        assert 'score' in health_factors['performance']

        # Deduplication health should be present
        assert 'deduplication' in health_factors
        assert 'score' in health_factors['deduplication']

    def test_system_maturity_calculation(self, intelligence_system):
        """Test calculation of system maturity."""
        maturity = intelligence_system._calculate_system_maturity()

        # With all features enabled, should be 'advanced'
        assert maturity == 'advanced'

    def test_system_maturity_minimal(self, mock_memory_system):
        """Test maturity calculation with no features."""
        del mock_memory_system.deduplicator
        del mock_memory_system.query_monitor
        del mock_memory_system.chunk_manager

        intelligence = MemoryIntelligenceSystem(mock_memory_system)
        maturity = intelligence._calculate_system_maturity()

        assert maturity == 'minimal'

    def test_storage_usage_estimation(self, intelligence_system):
        """Test estimation of storage usage."""
        usage_100 = intelligence_system._estimate_storage_usage(100)
        usage_1000 = intelligence_system._estimate_storage_usage(1000)

        assert isinstance(usage_100, float)
        assert isinstance(usage_1000, float)
        assert usage_1000 > usage_100

    def test_analytics_history_cleanup(self, intelligence_system):
        """Test cleanup of old analytics history."""
        # Add old and recent records
        old_time = time.time() - (35 * 86400)  # 35 days ago
        recent_time = time.time() - (10 * 86400)  # 10 days ago

        intelligence_system.analytics_history = [
            {'timestamp': old_time, 'total_documents': 100},
            {'timestamp': recent_time, 'total_documents': 150},
            {'timestamp': time.time(), 'total_documents': 175}
        ]

        intelligence_system._cleanup_analytics_history()

        # Should have removed old record
        assert len(intelligence_system.analytics_history) == 2

        # All remaining should be within retention period
        cutoff = time.time() - (30 * 86400)
        for record in intelligence_system.analytics_history:
            assert record['timestamp'] > cutoff

    def test_analytics_history_tracking(self, intelligence_system):
        """Test that generating analytics adds to history."""
        initial_count = len(intelligence_system.analytics_history)

        intelligence_system.generate_comprehensive_analytics()

        assert len(intelligence_system.analytics_history) == initial_count + 1

        # Check history entry has expected fields
        latest = intelligence_system.analytics_history[-1]
        assert 'timestamp' in latest
        assert 'total_documents' in latest
        assert 'health_score' in latest

    def test_error_handling_in_system_overview(self, mock_memory_system):
        """Test error handling when collection stats fail."""
        mock_memory_system.get_collection_stats.side_effect = Exception("Database error")

        intelligence = MemoryIntelligenceSystem(mock_memory_system)
        overview = intelligence._generate_system_overview()

        assert 'error' in overview

    def test_error_handling_in_deduplication(self, mock_memory_system):
        """Test error handling when deduplication stats fail."""
        mock_memory_system.deduplicator.get_deduplication_stats.side_effect = Exception("Dedup error")

        intelligence = MemoryIntelligenceSystem(mock_memory_system)
        dedup_analysis = intelligence._analyze_deduplication_effectiveness()

        assert 'error' in dedup_analysis

    def test_empty_collection_stats(self, mock_memory_system):
        """Test handling of empty collection stats."""
        mock_memory_system.get_collection_stats.return_value = {
            'collections': {}
        }

        intelligence = MemoryIntelligenceSystem(mock_memory_system)
        storage_analysis = intelligence._analyze_storage_patterns()

        assert storage_analysis['total_documents'] == 0
        assert storage_analysis['collection_distribution'] == {}
