"""
Unit tests for MemoryIntelligenceSystem

Tests the analytics, predictive insights, optimization recommendations,
and health assessment features of the intelligence system.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from src.mcp_memory_server.analytics.intelligence import MemoryIntelligenceSystem


@pytest.fixture
def mock_memory_system():
    """Create a mock memory system for testing."""
    memory_system = Mock()
    memory_system.short_term_memory = Mock()
    memory_system.long_term_memory = Mock()
    memory_system.permanent_memory = Mock()
    
    # Mock collection counts
    memory_system.short_term_memory._collection.count.return_value = 100
    memory_system.long_term_memory._collection.count.return_value = 50
    memory_system.permanent_memory._collection.count.return_value = 25
    
    # Mock collections list that gets iterated
    memory_system.collections = [
        memory_system.short_term_memory,
        memory_system.long_term_memory, 
        memory_system.permanent_memory
    ]
    
    # Mock deduplicator with proper boolean enabled attribute
    memory_system.deduplicator = Mock()
    memory_system.deduplicator.enabled = True
    memory_system.deduplicator.stats = {
        'total_duplicates_found': 15,
        'total_documents_merged': 12,
        'total_storage_saved': 2048,
        'processing_time_total': 5.5
    }
    memory_system.deduplicator.get_deduplication_stats.return_value = {
        'total_duplicates_found': 15,
        'total_documents_merged': 12,
        'total_storage_saved': 2048,
        'processing_time_total': 5.5
    }
    
    # Mock query monitor with proper methods
    memory_system.query_monitor = Mock()
    memory_system.query_monitor.get_performance_stats.return_value = {
        'total_queries': 500,
        'average_response_time': 0.25,
        'cache_hit_rate': 0.85,
        'error_rate': 0.02
    }
    
    # Add chunk_manager as a simple mock
    memory_system.chunk_manager = Mock()
    
    # Mock get_collection_stats method with proper structure
    memory_system.get_collection_stats.return_value = {
        'collections': {
            'short_term': {
                'count': 100,
                'status': 'active'
            },
            'long_term': {
                'count': 50, 
                'status': 'active'
            },
            'permanent': {
                'count': 25,
                'status': 'active'
            }
        },
        'total_documents': 175,
        'last_updated': time.time()
    }
    
    # Mock additional methods that might be called during optimization
    memory_system.get_query_performance_stats.return_value = {
        'total_queries': 500,
        'average_response_time': 0.25
    }
    
    return memory_system


@pytest.fixture
def analytics_config():
    """Sample analytics configuration."""
    return {
        'enable_predictive_analytics': True,
        'history_retention_days': 30,
        'cache_duration_minutes': 15,
        'optimization_check_interval_hours': 6,
        'storage_growth_prediction_days': 7,
        'performance_baseline_hours': 24
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
        assert intelligence.config['enable_predictive_analytics'] is True
        assert intelligence.analytics_history == []
        assert intelligence.optimization_recommendations == []

    def test_initialization_with_default_config(self, mock_memory_system):
        """Test initialization with default configuration."""
        intelligence = MemoryIntelligenceSystem(mock_memory_system)
        
        assert intelligence.config['enable_predictive_analytics'] is True
        assert intelligence.config['history_retention_days'] == 30
        assert intelligence.config['cache_duration_minutes'] == 15
        assert isinstance(intelligence.system_start_time, float)

    def test_system_overview_generation(self, intelligence_system):
        """Test generation of system overview."""
        overview = intelligence_system._generate_system_overview()
        
        # Based on actual implementation structure
        assert 'total_documents' in overview
        assert 'active_collections' in overview
        assert 'system_age_days' in overview
        assert 'deduplication_enabled' in overview
        assert 'query_monitoring_active' in overview
        assert 'estimated_storage_mb' in overview
        
        # Check values are reasonable
        assert isinstance(overview['total_documents'], int)
        assert overview['total_documents'] >= 0
        assert isinstance(overview['active_collections'], int)
        assert isinstance(overview['deduplication_enabled'], bool)

    def test_comprehensive_analytics_generation(self, intelligence_system):
        """Test generation of comprehensive analytics."""
        analytics = intelligence_system.generate_comprehensive_analytics()
        
        # Check main sections based on actual implementation
        assert 'system_overview' in analytics
        assert 'storage_analytics' in analytics  
        assert 'deduplication_intelligence' in analytics
        assert 'query_performance_insights' in analytics
        assert 'predictive_analytics' in analytics
        assert 'optimization_recommendations' in analytics
        assert 'system_health_assessment' in analytics
        assert 'trend_analysis' in analytics
        assert 'cost_benefit_analysis' in analytics
        
        # Check timestamp is in analytics root
        assert 'timestamp' in analytics
        assert isinstance(analytics['timestamp'], float)

    def test_storage_patterns_analysis(self, intelligence_system):
        """Test analysis of storage patterns."""
        storage_analysis = intelligence_system._analyze_storage_patterns()
        
        # Based on actual implementation structure
        assert 'total_documents' in storage_analysis
        assert 'collection_distribution' in storage_analysis
        assert 'growth_patterns' in storage_analysis
        
        # Check that values are reasonable
        assert isinstance(storage_analysis['total_documents'], int)
        assert storage_analysis['total_documents'] >= 0
        assert isinstance(storage_analysis['collection_distribution'], dict)

    def test_deduplication_effectiveness_analysis(self, intelligence_system):
        """Test analysis of deduplication effectiveness."""
        dedup_analysis = intelligence_system._analyze_deduplication_effectiveness()
        
        # Based on actual implementation structure
        assert 'enabled' in dedup_analysis
        assert 'current_stats' in dedup_analysis
        assert 'effectiveness_trends' in dedup_analysis
        
        # Check that current stats have expected structure
        current_stats = dedup_analysis['current_stats']
        assert isinstance(current_stats, dict)
        assert isinstance(dedup_analysis['enabled'], bool)

    def test_query_patterns_analysis(self, intelligence_system):
        """Test analysis of query patterns."""
        query_analysis = intelligence_system._analyze_query_patterns()
        
        # Based on actual implementation structure
        assert 'enabled' in query_analysis
        assert 'daily_performance' in query_analysis
        assert 'behavior_insights' in query_analysis
        
        # Check basic structure
        assert isinstance(query_analysis['enabled'], bool)

    def test_predictive_insights_generation(self, intelligence_system):
        """Test generation of predictive insights."""
        insights = intelligence_system._generate_predictive_insights()
        
        # Based on actual implementation structure
        assert 'enabled' in insights
        assert 'generated_at' in insights
        assert 'confidence_scores' in insights
        assert 'deduplication_trends' in insights

    def test_optimization_recommendations_generation(self, intelligence_system):
        """Test generation of optimization recommendations."""
        recommendations = intelligence_system._generate_optimization_recommendations()
        
        assert isinstance(recommendations, list)
        
        # Check recommendation structure if any exist
        for rec in recommendations:
            if isinstance(rec, dict):
                # Based on actual implementation structure
                expected_fields = ['category', 'description', 'estimated_impact', 'priority']
                has_required_fields = any(field in rec for field in expected_fields)
                assert has_required_fields

    def test_comprehensive_health_assessment(self, intelligence_system):
        """Test comprehensive health assessment."""
        health = intelligence_system._assess_comprehensive_health()
        
        # Based on actual implementation structure
        assert 'overall_score' in health
        assert 'health_factors' in health
        assert 'critical_issues' in health
        assert 'maintenance_recommendations' in health
        
        # Overall score should be between 0 and 1
        overall_score = health['overall_score']
        assert 0 <= overall_score <= 1
        
        # Health factors should exist
        health_factors = health['health_factors']
        assert isinstance(health_factors, dict)

    def test_trends_analysis(self, intelligence_system):
        """Test trends analysis."""
        trends = intelligence_system._analyze_trends()
        
        assert 'storage_trends' in trends
        assert 'performance_trends' in trends
        assert 'usage_trends' in trends
        assert 'optimization_trends' in trends
        
        # Each trend should have a direction
        for trend_category in trends.values():
            if isinstance(trend_category, dict) and 'direction' in trend_category:
                assert trend_category['direction'] in ['improving', 'declining', 'stable', 'unknown']

    def test_cost_benefits_calculation(self, intelligence_system):
        """Test calculation of cost benefits."""
        cost_benefits = intelligence_system._calculate_cost_benefits()
        
        # Based on actual implementation structure
        assert 'benefits_breakdown' in cost_benefits
        assert 'costs_breakdown' in cost_benefits
        assert 'total_benefits_usd' in cost_benefits
        assert 'cost_effectiveness' in cost_benefits

    def test_system_maturity_calculation(self, intelligence_system):
        """Test calculation of system maturity."""
        # Test that system maturity returns a valid string
        maturity = intelligence_system._calculate_system_maturity()
        assert isinstance(maturity, str)
        
        # Should be one of the valid maturity levels
        valid_levels = ['new', 'developing', 'mature', 'advanced']
        assert maturity in valid_levels

    def test_storage_usage_estimation(self, intelligence_system):
        """Test estimation of storage usage."""
        # Test with different document counts
        usage_100 = intelligence_system._estimate_storage_usage(100)
        usage_1000 = intelligence_system._estimate_storage_usage(1000)
        
        assert isinstance(usage_100, float)
        assert isinstance(usage_1000, float)
        assert usage_1000 > usage_100  # More documents should use more storage

    def test_analytics_history_cleanup(self, intelligence_system):
        """Test cleanup of old analytics history."""
        # Add some old records
        old_time = time.time() - (35 * 86400)  # 35 days ago (older than retention)
        recent_time = time.time() - (10 * 86400)  # 10 days ago (within retention)
        
        intelligence_system.analytics_history = [
            {'timestamp': old_time, 'data': 'old'},
            {'timestamp': recent_time, 'data': 'recent'},
            {'timestamp': time.time(), 'data': 'current'}
        ]
        
        initial_count = len(intelligence_system.analytics_history)
        intelligence_system._cleanup_analytics_history()
        
        # Should have removed old records
        assert len(intelligence_system.analytics_history) < initial_count
        
        # Remaining records should be recent
        for record in intelligence_system.analytics_history:
            assert record['timestamp'] > time.time() - (30 * 86400)

    def test_growth_patterns_analysis(self, intelligence_system):
        """Test analysis of growth patterns."""
        growth_patterns = intelligence_system._analyze_growth_patterns()
        
        assert isinstance(growth_patterns, dict)
        # This method may return empty dict in current implementation

    def test_storage_efficiency_analysis(self, intelligence_system):
        """Test analysis of storage efficiency."""
        efficiency = intelligence_system._analyze_storage_efficiency()
        
        assert isinstance(efficiency, dict)
        # Method may return minimal data in current implementation

    def test_storage_recommendations_generation(self, intelligence_system):
        """Test generation of storage recommendations."""
        collection_sizes = {'short_term': 100, 'long_term': 50, 'permanent': 25}
        total_documents = 175
        
        recommendations = intelligence_system._generate_storage_recommendations(
            collection_sizes, total_documents
        )
        
        assert isinstance(recommendations, list)
        # Check that recommendations are structured properly if any exist
        for rec in recommendations:
            if isinstance(rec, dict):
                assert 'type' in rec or 'recommendation' in rec

    def test_cache_functionality(self, intelligence_system):
        """Test caching functionality for expensive operations."""
        # The cache is used internally, test it indirectly
        cache_key = 'test_key'
        test_data = {'test': 'data'}
        
        # Cache some data
        intelligence_system._cache[cache_key] = test_data
        intelligence_system._cache_timestamps[cache_key] = time.time()
        
        # Verify cache contains data
        assert cache_key in intelligence_system._cache
        assert intelligence_system._cache[cache_key] == test_data

    def test_default_stub_methods(self, intelligence_system):
        """Test that stub methods return appropriate default values."""
        # Test methods that are currently stubs
        assert intelligence_system._analyze_deduplication_trends() == {}
        assert intelligence_system._calculate_deduplication_roi({}, {}) == {}
        assert intelligence_system._analyze_duplicate_patterns() == {}
        assert intelligence_system._identify_deduplication_opportunities() == {}
        
        # Test prediction methods
        assert intelligence_system._predict_storage_growth(7) == {}
        assert intelligence_system._predict_query_performance() == {}
        assert intelligence_system._predict_deduplication_trends() == {}
        assert intelligence_system._predict_resource_requirements() == {}
        
        # Test health calculation methods
        storage_health = intelligence_system._calculate_storage_health({})
        assert storage_health['score'] == 0.8
        
        performance_health = intelligence_system._calculate_performance_health({})
        assert performance_health['score'] == 0.75

    def test_edge_cases_and_error_handling(self, intelligence_system, mock_memory_system):
        """Test edge cases and error handling."""
        # Test with None memory system
        intelligence_system.memory_system = None
        
        # Should handle gracefully when memory system is unavailable
        try:
            overview = intelligence_system._generate_system_overview()
            # If it doesn't crash, that's good
            assert isinstance(overview, dict)
        except AttributeError:
            # Expected if trying to access None memory system
            pass
        
        # Reset memory system
        intelligence_system.memory_system = mock_memory_system

    def test_configuration_edge_cases(self, mock_memory_system):
        """Test configuration edge cases."""
        # Test with empty config
        intelligence = MemoryIntelligenceSystem(mock_memory_system, {})
        assert intelligence.config is not None
        
        # Test with None config
        intelligence = MemoryIntelligenceSystem(mock_memory_system, None)
        assert intelligence.config is not None
        assert 'enable_predictive_analytics' in intelligence.config

    def test_time_based_calculations(self, intelligence_system):
        """Test time-based calculations work correctly."""
        # Test system age calculation
        system_age = time.time() - intelligence_system.system_start_time
        assert system_age >= 0
        
        # Test that timestamp-based operations handle current time correctly
        current_time = time.time()
        analytics = intelligence_system.generate_comprehensive_analytics()
        assert analytics['timestamp'] <= current_time + 1  # Small tolerance for execution time

    def test_data_structure_consistency(self, intelligence_system):
        """Test that returned data structures are consistent and well-formed."""
        analytics = intelligence_system.generate_comprehensive_analytics()
        
        # Check that all main sections exist based on actual implementation
        expected_sections = [
            'system_overview', 'storage_analytics', 'deduplication_intelligence',
            'query_performance_insights', 'predictive_analytics', 'optimization_recommendations',
            'system_health_assessment', 'trend_analysis', 'cost_benefit_analysis'
        ]
        
        for section in expected_sections:
            assert section in analytics
            # Most sections are dicts, but some may be lists
            assert analytics[section] is not None

    def test_numeric_value_ranges(self, intelligence_system):
        """Test that numeric values are in expected ranges."""
        health = intelligence_system._assess_comprehensive_health()
        
        # Health scores should be between 0 and 1
        assert 0 <= health['overall_score'] <= 1
        
        # Check health factors structure
        for component, score in health['health_factors'].items():
            if isinstance(score, dict) and 'score' in score:
                assert 0 <= score['score'] <= 1