"""
Simple unit tests for MemoryIntelligenceSystem

Tests core functionality with minimal mocking to verify
the simplified analytics system works correctly.
"""

import pytest
import time
from unittest.mock import Mock
from src.mcp_memory_server.analytics.intelligence import MemoryIntelligenceSystem


@pytest.fixture
def mock_memory_system():
    """Create a minimal mock memory system for testing."""
    memory_system = Mock()

    # Mock deduplicator
    memory_system.deduplicator = Mock()
    memory_system.deduplicator.enabled = True
    memory_system.deduplicator.get_deduplication_stats.return_value = {
        'total_duplicates_found': 10,
        'deduplication_efficiency': 20.0
    }

    # Mock query monitor
    memory_system.query_monitor = Mock()

    # Mock chunk_manager
    memory_system.chunk_manager = Mock()
    memory_system.chunk_manager.get_relationship_statistics.return_value = {}

    # Mock get_collection_stats
    memory_system.get_collection_stats.return_value = {
        'collections': {
            'short_term_memory': {'count': 50, 'status': 'active'},
            'long_term_memory': {'count': 30, 'status': 'active'}
        }
    }

    # Mock get_query_performance_stats
    memory_system.get_query_performance_stats.return_value = {
        'query_count': 100,
        'response_time_stats': {'mean_ms': 200.0}
    }

    return memory_system


@pytest.fixture
def intelligence_system(mock_memory_system):
    """Create MemoryIntelligenceSystem instance."""
    return MemoryIntelligenceSystem(mock_memory_system)


class TestMemoryIntelligenceSystemBasic:
    """Basic test suite for MemoryIntelligenceSystem."""

    def test_initialization_default(self, mock_memory_system):
        """Test initialization with default configuration."""
        intelligence = MemoryIntelligenceSystem(mock_memory_system)

        assert intelligence.memory_system == mock_memory_system
        assert isinstance(intelligence.config, dict)
        assert intelligence.config['history_retention_days'] == 30

    def test_initialization_custom_config(self, mock_memory_system):
        """Test initialization with custom configuration."""
        custom_config = {'history_retention_days': 7}
        intelligence = MemoryIntelligenceSystem(mock_memory_system, custom_config)

        assert intelligence.config == custom_config

    def test_system_overview_generation(self, intelligence_system):
        """Test generation of system overview."""
        overview = intelligence_system._generate_system_overview()

        assert isinstance(overview, dict)
        assert 'total_documents' in overview
        assert 'active_collections' in overview
        assert 'uptime_hours' in overview
        assert 'deduplication_enabled' in overview
        assert 'system_maturity' in overview

        assert overview['total_documents'] == 80
        assert overview['active_collections'] == 2

    def test_comprehensive_analytics_generation(self, intelligence_system):
        """Test generation of comprehensive analytics."""
        analytics = intelligence_system.generate_comprehensive_analytics()

        assert isinstance(analytics, dict)
        assert 'timestamp' in analytics
        assert 'system_overview' in analytics
        assert 'storage_analytics' in analytics
        assert 'deduplication_intelligence' in analytics
        assert 'query_performance_insights' in analytics
        assert 'optimization_recommendations' in analytics
        assert 'system_health_assessment' in analytics

        # Deprecated features should return not_implemented
        assert analytics['predictive_analytics']['status'] == 'not_implemented'
        assert analytics['trend_analysis']['status'] == 'not_implemented'
        assert analytics['cost_benefit_analysis']['status'] == 'not_implemented'

    def test_storage_patterns_analysis(self, intelligence_system):
        """Test analysis of storage patterns."""
        storage = intelligence_system._analyze_storage_patterns()

        assert isinstance(storage, dict)
        assert 'total_documents' in storage
        assert 'collection_distribution' in storage
        assert 'recommendations' in storage

        assert storage['total_documents'] == 80

    def test_deduplication_effectiveness_analysis(self, intelligence_system):
        """Test analysis of deduplication effectiveness."""
        dedup = intelligence_system._analyze_deduplication_effectiveness()

        assert dedup['enabled'] is True
        assert 'current_stats' in dedup
        assert dedup['current_stats']['total_duplicates_found'] == 10

    def test_deduplication_disabled(self, mock_memory_system):
        """Test when deduplication is disabled."""
        mock_memory_system.deduplicator.enabled = False
        intelligence = MemoryIntelligenceSystem(mock_memory_system)

        dedup = intelligence._analyze_deduplication_effectiveness()

        assert dedup['enabled'] is False

    def test_query_patterns_analysis(self, intelligence_system):
        """Test analysis of query patterns."""
        query = intelligence_system._analyze_query_patterns()

        assert query['enabled'] is True
        assert 'daily_performance' in query
        assert 'weekly_performance' in query

    def test_query_patterns_without_monitor(self, mock_memory_system):
        """Test when query monitor not available."""
        del mock_memory_system.query_monitor
        intelligence = MemoryIntelligenceSystem(mock_memory_system)

        query = intelligence._analyze_query_patterns()

        assert query['enabled'] is False

    def test_optimization_recommendations(self, intelligence_system):
        """Test optimization recommendations generation."""
        recs = intelligence_system._generate_optimization_recommendations()

        assert isinstance(recs, list)
        for rec in recs:
            assert 'priority' in rec
            assert 'category' in rec
            assert 'title' in rec

    def test_system_health_assessment(self, intelligence_system):
        """Test system health assessment."""
        health = intelligence_system._assess_system_health()

        assert 'overall_score' in health
        assert 'status' in health
        assert 'health_factors' in health

        assert 0 <= health['overall_score'] <= 1
        assert health['status'] in ['excellent', 'good', 'fair', 'needs_attention']

    def test_system_maturity_advanced(self, intelligence_system):
        """Test maturity calculation with all features."""
        maturity = intelligence_system._calculate_system_maturity()
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
        """Test storage usage estimation."""
        small = intelligence_system._estimate_storage_usage(100)
        large = intelligence_system._estimate_storage_usage(1000)

        assert large > small

    def test_analytics_history_cleanup(self, intelligence_system):
        """Test cleanup of old history."""
        old_time = time.time() - (35 * 86400)
        recent_time = time.time()

        intelligence_system.analytics_history = [
            {'timestamp': old_time},
            {'timestamp': recent_time}
        ]

        intelligence_system._cleanup_analytics_history()

        # Old record should be removed
        assert len(intelligence_system.analytics_history) == 1

    def test_analytics_history_tracking(self, intelligence_system):
        """Test that analytics are tracked in history."""
        intelligence_system.generate_comprehensive_analytics()

        assert len(intelligence_system.analytics_history) == 1
        assert 'timestamp' in intelligence_system.analytics_history[0]
        assert 'total_documents' in intelligence_system.analytics_history[0]

    def test_error_handling(self, mock_memory_system):
        """Test error handling in system overview."""
        mock_memory_system.get_collection_stats.side_effect = Exception("Error")

        intelligence = MemoryIntelligenceSystem(mock_memory_system)
        overview = intelligence._generate_system_overview()

        assert 'error' in overview

    def test_empty_collections(self, mock_memory_system):
        """Test handling of empty collections."""
        mock_memory_system.get_collection_stats.return_value = {'collections': {}}

        intelligence = MemoryIntelligenceSystem(mock_memory_system)
        storage = intelligence._analyze_storage_patterns()

        assert storage['total_documents'] == 0

    def test_comprehensive_workflow(self, intelligence_system):
        """Test complete workflow without errors."""
        analytics = intelligence_system.generate_comprehensive_analytics()

        assert isinstance(analytics, dict)
        assert len(analytics) > 0
        assert 'system_overview' in analytics
        assert 'system_health_assessment' in analytics
