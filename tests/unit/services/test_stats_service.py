"""
Unit tests for MemoryStatsService

Comprehensive tests for statistics and analytics aggregation including:
- Collection statistics
- Query performance stats
- Comprehensive analytics
- Chunk relationship stats
- Dynamic collection registration
"""

import pytest
from unittest.mock import Mock, patch

from src.mcp_memory_server.memory.services.stats import MemoryStatsService


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_short_term_memory():
    """Create a mock short-term memory Chroma collection."""
    mock = Mock()
    mock._collection = Mock()
    mock._collection.count.return_value = 100
    mock.get.return_value = {'ids': ['id1', 'id2', 'id3']}
    return mock


@pytest.fixture
def mock_long_term_memory():
    """Create a mock long-term memory Chroma collection."""
    mock = Mock()
    mock._collection = Mock()
    mock._collection.count.return_value = 500
    mock.get.return_value = {'ids': ['id1', 'id2']}
    return mock


@pytest.fixture
def mock_query_monitor():
    """Create a mock QueryPerformanceMonitor."""
    mock = Mock()
    mock.get_performance_summary.return_value = {
        'query_count': 150,
        'response_time_stats': {
            'mean_ms': 125.5,
            'min_ms': 10.0,
            'max_ms': 500.0,
            'p95_ms': 300.0
        },
        'slow_queries': 5,
        'fast_queries': 140
    }
    return mock


@pytest.fixture
def mock_intelligence_system():
    """Create a mock MemoryIntelligenceSystem."""
    mock = Mock()
    mock.generate_comprehensive_analytics.return_value = {
        'system_overview': {
            'total_documents': 600,
            'memory_utilization': 0.75
        },
        'predictions': {
            'growth_rate': 10.5,
            'maintenance_recommended': False
        },
        'recommendations': [
            'Consider archiving old memories',
            'Query performance is optimal'
        ]
    }
    return mock


@pytest.fixture
def mock_chunk_manager():
    """Create a mock ChunkRelationshipManager."""
    mock = Mock()
    mock.get_relationship_statistics.return_value = {
        'total_chunks_analyzed': 250,
        'total_relationships_found': 120,
        'relationship_types_distribution': {
            'semantic_similarity': 80,
            'co_occurrence': 30,
            'temporal': 10
        },
        'orphan_chunks': 15,
        'health_score': 0.92
    }
    return mock


@pytest.fixture
def stats_service(
    mock_short_term_memory,
    mock_long_term_memory,
    mock_query_monitor,
    mock_intelligence_system,
    mock_chunk_manager
):
    """Create a MemoryStatsService instance with all mocked dependencies."""
    return MemoryStatsService(
        short_term_memory=mock_short_term_memory,
        long_term_memory=mock_long_term_memory,
        query_monitor=mock_query_monitor,
        intelligence_system=mock_intelligence_system,
        chunk_manager=mock_chunk_manager
    )


@pytest.fixture
def stats_service_no_chunk_manager(
    mock_short_term_memory,
    mock_long_term_memory,
    mock_query_monitor,
    mock_intelligence_system
):
    """Create a MemoryStatsService instance without chunk manager."""
    return MemoryStatsService(
        short_term_memory=mock_short_term_memory,
        long_term_memory=mock_long_term_memory,
        query_monitor=mock_query_monitor,
        intelligence_system=mock_intelligence_system,
        chunk_manager=None
    )


# =============================================================================
# Initialization Tests
# =============================================================================

class TestMemoryStatsServiceInit:
    """Tests for MemoryStatsService initialization."""

    def test_initialization_sets_dependencies(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_query_monitor,
        mock_intelligence_system,
        mock_chunk_manager
    ):
        """Test that initialization properly sets all dependencies."""
        service = MemoryStatsService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            query_monitor=mock_query_monitor,
            intelligence_system=mock_intelligence_system,
            chunk_manager=mock_chunk_manager
        )

        assert service.short_term_memory is mock_short_term_memory
        assert service.long_term_memory is mock_long_term_memory
        assert service.query_monitor is mock_query_monitor
        assert service.intelligence_system is mock_intelligence_system
        assert service.chunk_manager is mock_chunk_manager

    def test_initialization_creates_empty_additional_collections(
            self, stats_service):
        """Test that initialization creates an empty additional collections dict."""
        assert stats_service._additional_collections == {}

    def test_initialization_with_none_chunk_manager(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_query_monitor,
        mock_intelligence_system
    ):
        """Test that service can be initialized with None chunk_manager."""
        service = MemoryStatsService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            query_monitor=mock_query_monitor,
            intelligence_system=mock_intelligence_system,
            chunk_manager=None
        )

        assert service.chunk_manager is None


# =============================================================================
# register_collection Tests
# =============================================================================

class TestRegisterCollection:
    """Tests for the register_collection method."""

    def test_register_single_collection(self, stats_service):
        """Test registering a single additional collection."""
        mock_collection = Mock()

        stats_service.register_collection('semantic_memory', mock_collection)

        assert 'semantic_memory' in stats_service._additional_collections
        assert stats_service._additional_collections['semantic_memory'] is mock_collection

    def test_register_multiple_collections(self, stats_service):
        """Test registering multiple additional collections."""
        mock_semantic = Mock()
        mock_episodic = Mock()
        mock_working = Mock()

        stats_service.register_collection('semantic', mock_semantic)
        stats_service.register_collection('episodic', mock_episodic)
        stats_service.register_collection('working', mock_working)

        assert len(stats_service._additional_collections) == 3
        assert stats_service._additional_collections['semantic'] is mock_semantic
        assert stats_service._additional_collections['episodic'] is mock_episodic
        assert stats_service._additional_collections['working'] is mock_working

    def test_register_collection_overwrites_existing(self, stats_service):
        """Test that registering a collection with existing name overwrites it."""
        mock_old = Mock()
        mock_new = Mock()

        stats_service.register_collection('test_collection', mock_old)
        stats_service.register_collection('test_collection', mock_new)

        assert stats_service._additional_collections['test_collection'] is mock_new

    def test_get_all_collections_includes_registered(self, stats_service):
        """Test that _get_all_collections includes registered collections."""
        mock_additional = Mock()
        stats_service.register_collection('additional', mock_additional)

        collections = stats_service._get_all_collections()

        assert 'short_term' in collections
        assert 'long_term' in collections
        assert 'additional' in collections
        assert len(collections) == 3


# =============================================================================
# get_collection_stats Tests
# =============================================================================

class TestGetCollectionStats:
    """Tests for the get_collection_stats method."""

    def test_get_collection_stats_success(self, stats_service):
        """Test getting collection stats for default collections."""
        stats = stats_service.get_collection_stats()

        assert 'collections' in stats
        assert 'short_term' in stats['collections']
        assert 'long_term' in stats['collections']

        assert stats['collections']['short_term']['count'] == 100
        assert stats['collections']['short_term']['status'] == 'active'

        assert stats['collections']['long_term']['count'] == 500
        assert stats['collections']['long_term']['status'] == 'active'

    def test_get_collection_stats_uses_collection_count(self, stats_service):
        """Test that stats use ChromaDB's _collection.count() method."""
        stats_service.get_collection_stats()

        stats_service.short_term_memory._collection.count.assert_called_once()
        stats_service.long_term_memory._collection.count.assert_called_once()

    def test_get_collection_stats_fallback_to_get(self, stats_service):
        """Test fallback to get() when _collection is not available."""
        # Remove _collection attribute
        del stats_service.short_term_memory._collection

        stats = stats_service.get_collection_stats()

        # Should fallback to get() and count IDs
        stats_service.short_term_memory.get.assert_called()
        # len of mock ids
        assert stats['collections']['short_term']['count'] == 3
        assert stats['collections']['short_term']['status'] == 'active'

    def test_get_collection_stats_includes_additional_collections(
            self, stats_service):
        """Test that stats include additional registered collections."""
        mock_additional = Mock()
        mock_additional._collection = Mock()
        mock_additional._collection.count.return_value = 75

        stats_service.register_collection('semantic', mock_additional)
        stats = stats_service.get_collection_stats()

        assert 'semantic' in stats['collections']
        assert stats['collections']['semantic']['count'] == 75
        assert stats['collections']['semantic']['status'] == 'active'

    def test_get_collection_stats_handles_collection_error(
            self, stats_service):
        """Test error handling when a collection fails."""
        stats_service.short_term_memory._collection.count.side_effect = Exception(
            "Connection failed")

        stats = stats_service.get_collection_stats()

        assert stats['collections']['short_term']['count'] == 0
        assert 'error: Connection failed' in stats['collections']['short_term']['status']
        # Long-term should still work
        assert stats['collections']['long_term']['count'] == 500

    def test_get_collection_stats_handles_partial_errors(self, stats_service):
        """Test that partial errors don't affect other collections."""
        mock_failing = Mock()
        mock_failing._collection = Mock()
        mock_failing._collection.count.side_effect = Exception("DB error")

        mock_working = Mock()
        mock_working._collection = Mock()
        mock_working._collection.count.return_value = 42

        stats_service.register_collection('failing', mock_failing)
        stats_service.register_collection('working', mock_working)

        stats = stats_service.get_collection_stats()

        assert stats['collections']['failing']['count'] == 0
        assert 'error' in stats['collections']['failing']['status']
        assert stats['collections']['working']['count'] == 42
        assert stats['collections']['working']['status'] == 'active'

    def test_get_collection_stats_empty_collection(self, stats_service):
        """Test stats for empty collections."""
        stats_service.short_term_memory._collection.count.return_value = 0

        stats = stats_service.get_collection_stats()

        assert stats['collections']['short_term']['count'] == 0
        assert stats['collections']['short_term']['status'] == 'active'

    def test_get_collection_stats_get_fallback_empty_ids(self, stats_service):
        """Test fallback to get() with empty result."""
        del stats_service.short_term_memory._collection
        stats_service.short_term_memory.get.return_value = {}

        stats = stats_service.get_collection_stats()

        assert stats['collections']['short_term']['count'] == 0


# =============================================================================
# get_query_performance_stats Tests
# =============================================================================

class TestGetQueryPerformanceStats:
    """Tests for the get_query_performance_stats method."""

    def test_get_query_performance_stats_default(self, stats_service):
        """Test getting query performance stats with default time window."""
        stats = stats_service.get_query_performance_stats()

        assert stats['query_count'] == 150
        assert stats['response_time_stats']['mean_ms'] == 125.5
        stats_service.query_monitor.get_performance_summary.assert_called_once_with(
            'all')

    def test_get_query_performance_stats_hour_window(self, stats_service):
        """Test getting stats with hour time window."""
        stats_service.get_query_performance_stats(time_window='hour')

        stats_service.query_monitor.get_performance_summary.assert_called_once_with(
            'hour')

    def test_get_query_performance_stats_day_window(self, stats_service):
        """Test getting stats with day time window."""
        stats_service.get_query_performance_stats(time_window='day')

        stats_service.query_monitor.get_performance_summary.assert_called_once_with(
            'day')

    def test_get_query_performance_stats_week_window(self, stats_service):
        """Test getting stats with week time window."""
        stats_service.get_query_performance_stats(time_window='week')

        stats_service.query_monitor.get_performance_summary.assert_called_once_with(
            'week')

    def test_get_query_performance_stats_all_window(self, stats_service):
        """Test getting stats with all time window."""
        stats_service.get_query_performance_stats(time_window='all')

        stats_service.query_monitor.get_performance_summary.assert_called_once_with(
            'all')

    def test_get_query_performance_stats_error_handling(self, stats_service):
        """Test error handling when query monitor fails."""
        stats_service.query_monitor.get_performance_summary.side_effect = Exception(
            "Monitor error")

        with patch('logging.warning') as mock_log:
            stats = stats_service.get_query_performance_stats()

            assert 'error' in stats
            assert stats['error'] == 'Monitor error'
            assert stats['message'] == 'Query monitoring not available'
            mock_log.assert_called_once()

    def test_get_query_performance_stats_returns_full_data(
            self, stats_service):
        """Test that all performance data is returned."""
        stats = stats_service.get_query_performance_stats()

        assert 'query_count' in stats
        assert 'response_time_stats' in stats
        assert 'slow_queries' in stats
        assert 'fast_queries' in stats
        assert stats['response_time_stats']['p95_ms'] == 300.0


# =============================================================================
# get_comprehensive_analytics Tests
# =============================================================================

class TestGetComprehensiveAnalytics:
    """Tests for the get_comprehensive_analytics method."""

    def test_get_comprehensive_analytics_success(self, stats_service):
        """Test getting comprehensive analytics successfully."""
        analytics = stats_service.get_comprehensive_analytics()

        assert 'system_overview' in analytics
        assert 'predictions' in analytics
        assert 'recommendations' in analytics
        stats_service.intelligence_system.generate_comprehensive_analytics.assert_called_once()

    def test_get_comprehensive_analytics_system_overview(self, stats_service):
        """Test system overview in analytics."""
        analytics = stats_service.get_comprehensive_analytics()

        overview = analytics['system_overview']
        assert overview['total_documents'] == 600
        assert overview['memory_utilization'] == 0.75

    def test_get_comprehensive_analytics_predictions(self, stats_service):
        """Test predictions in analytics."""
        analytics = stats_service.get_comprehensive_analytics()

        predictions = analytics['predictions']
        assert predictions['growth_rate'] == 10.5
        assert predictions['maintenance_recommended'] is False

    def test_get_comprehensive_analytics_recommendations(self, stats_service):
        """Test recommendations in analytics."""
        analytics = stats_service.get_comprehensive_analytics()

        recommendations = analytics['recommendations']
        assert len(recommendations) == 2
        assert 'Consider archiving old memories' in recommendations

    def test_get_comprehensive_analytics_error_handling(self, stats_service):
        """Test error handling when intelligence system fails."""
        stats_service.intelligence_system.generate_comprehensive_analytics.side_effect = Exception(
            "Analytics error")

        with patch('logging.warning') as mock_log:
            analytics = stats_service.get_comprehensive_analytics()

            assert 'error' in analytics
            assert analytics['error'] == 'Analytics error'
            assert analytics['message'] == 'Analytics system not available'
            mock_log.assert_called_once()

    def test_get_comprehensive_analytics_empty_response(self, stats_service):
        """Test handling of empty analytics response."""
        stats_service.intelligence_system.generate_comprehensive_analytics.return_value = {}

        analytics = stats_service.get_comprehensive_analytics()

        assert analytics == {}


# =============================================================================
# get_chunk_relationship_stats Tests
# =============================================================================

class TestGetChunkRelationshipStats:
    """Tests for the get_chunk_relationship_stats method."""

    def test_get_chunk_relationship_stats_success(self, stats_service):
        """Test getting chunk relationship stats successfully."""
        stats = stats_service.get_chunk_relationship_stats()

        assert stats['total_chunks_analyzed'] == 250
        assert stats['total_relationships_found'] == 120
        stats_service.chunk_manager.get_relationship_statistics.assert_called_once()

    def test_get_chunk_relationship_stats_distribution(self, stats_service):
        """Test relationship type distribution in stats."""
        stats = stats_service.get_chunk_relationship_stats()

        distribution = stats['relationship_types_distribution']
        assert distribution['semantic_similarity'] == 80
        assert distribution['co_occurrence'] == 30
        assert distribution['temporal'] == 10

    def test_get_chunk_relationship_stats_health_metrics(self, stats_service):
        """Test health metrics in chunk relationship stats."""
        stats = stats_service.get_chunk_relationship_stats()

        assert stats['orphan_chunks'] == 15
        assert stats['health_score'] == 0.92

    def test_get_chunk_relationship_stats_no_chunk_manager(
            self, stats_service_no_chunk_manager):
        """Test error response when chunk manager is None."""
        stats = stats_service_no_chunk_manager.get_chunk_relationship_stats()

        assert 'error' in stats
        assert stats['error'] == 'Chunk relationship manager not available'

    def test_get_chunk_relationship_stats_error_handling(self, stats_service):
        """Test error handling when chunk manager fails."""
        stats_service.chunk_manager.get_relationship_statistics.side_effect = Exception(
            "Chunk error")

        with patch('logging.warning') as mock_log:
            stats = stats_service.get_chunk_relationship_stats()

            assert 'error' in stats
            assert stats['error'] == 'Chunk error'
            assert stats['message'] == 'Chunk relationship tracking not available'
            mock_log.assert_called_once()

    def test_get_chunk_relationship_stats_empty_response(self, stats_service):
        """Test handling of empty chunk stats response."""
        stats_service.chunk_manager.get_relationship_statistics.return_value = {}

        stats = stats_service.get_chunk_relationship_stats()

        assert stats == {}


# =============================================================================
# Integration / Edge Case Tests
# =============================================================================

class TestMemoryStatsServiceEdgeCases:
    """Edge case and integration tests."""

    def test_all_methods_independent(self, stats_service):
        """Test that all methods can be called independently."""
        # Call all methods in various orders
        stats_service.get_collection_stats()
        stats_service.get_query_performance_stats()
        stats_service.get_comprehensive_analytics()
        stats_service.get_chunk_relationship_stats()

        # Call again in different order
        stats_service.get_chunk_relationship_stats()
        stats_service.get_collection_stats()

        # All should work without side effects

    def test_multiple_errors_handled_independently(self, stats_service):
        """Test that errors in one method don't affect others."""
        stats_service.query_monitor.get_performance_summary.side_effect = Exception(
            "Error 1")
        stats_service.intelligence_system.generate_comprehensive_analytics.side_effect = Exception(
            "Error 2")

        # These should fail gracefully
        query_stats = stats_service.get_query_performance_stats()
        analytics = stats_service.get_comprehensive_analytics()

        # These should still work
        collection_stats = stats_service.get_collection_stats()
        chunk_stats = stats_service.get_chunk_relationship_stats()

        assert 'error' in query_stats
        assert 'error' in analytics
        assert 'collections' in collection_stats
        assert 'total_chunks_analyzed' in chunk_stats

    def test_large_collection_counts(self, stats_service):
        """Test handling of large collection counts."""
        stats_service.short_term_memory._collection.count.return_value = 10_000_000
        stats_service.long_term_memory._collection.count.return_value = 50_000_000

        stats = stats_service.get_collection_stats()

        assert stats['collections']['short_term']['count'] == 10_000_000
        assert stats['collections']['long_term']['count'] == 50_000_000

    def test_unicode_in_error_messages(self, stats_service):
        """Test handling of unicode in error messages."""
        stats_service.short_term_memory._collection.count.side_effect = Exception(
            "Error: 日本語メッセージ")

        stats = stats_service.get_collection_stats()

        assert 'error: Error: 日本語メッセージ' in stats['collections']['short_term']['status']

    def test_concurrent_collection_registration(self, stats_service):
        """Test registering collections and getting stats."""
        # Register collections
        for i in range(10):
            mock = Mock()
            mock._collection = Mock()
            mock._collection.count.return_value = i * 10
            stats_service.register_collection(f'collection_{i}', mock)

        stats = stats_service.get_collection_stats()

        # Should have 12 collections total (2 default + 10 registered)
        assert len(stats['collections']) == 12

        for i in range(10):
            assert stats['collections'][f'collection_{i}']['count'] == i * 10

    def test_get_all_collections_returns_copy_safe_dict(self, stats_service):
        """Test that _get_all_collections returns expected structure."""
        collections = stats_service._get_all_collections()

        assert 'short_term' in collections
        assert 'long_term' in collections
        assert collections['short_term'] is stats_service.short_term_memory
        assert collections['long_term'] is stats_service.long_term_memory

    def test_collection_with_no_ids_key_in_get_result(self, stats_service):
        """Test fallback when get() returns dict without ids key."""
        del stats_service.short_term_memory._collection
        stats_service.short_term_memory.get.return_value = {'documents': []}

        stats = stats_service.get_collection_stats()

        assert stats['collections']['short_term']['count'] == 0


# =============================================================================
# Type Safety Tests
# =============================================================================

class TestMemoryStatsServiceTypes:
    """Tests for type safety and return value contracts."""

    def test_get_collection_stats_returns_dict(self, stats_service):
        """Test that get_collection_stats returns a dict."""
        result = stats_service.get_collection_stats()
        assert isinstance(result, dict)
        assert isinstance(result.get('collections'), dict)

    def test_get_query_performance_stats_returns_dict(self, stats_service):
        """Test that get_query_performance_stats returns a dict."""
        result = stats_service.get_query_performance_stats()
        assert isinstance(result, dict)

    def test_get_comprehensive_analytics_returns_dict(self, stats_service):
        """Test that get_comprehensive_analytics returns a dict."""
        result = stats_service.get_comprehensive_analytics()
        assert isinstance(result, dict)

    def test_get_chunk_relationship_stats_returns_dict(self, stats_service):
        """Test that get_chunk_relationship_stats returns a dict."""
        result = stats_service.get_chunk_relationship_stats()
        assert isinstance(result, dict)

    def test_error_responses_are_dicts(self, stats_service):
        """Test that error responses are properly formatted dicts."""
        stats_service.query_monitor.get_performance_summary.side_effect = Exception(
            "Test")
        stats_service.intelligence_system.generate_comprehensive_analytics.side_effect = Exception(
            "Test")
        stats_service.chunk_manager.get_relationship_statistics.side_effect = Exception(
            "Test")

        query_result = stats_service.get_query_performance_stats()
        analytics_result = stats_service.get_comprehensive_analytics()
        chunk_result = stats_service.get_chunk_relationship_stats()

        for result in [query_result, analytics_result, chunk_result]:
            assert isinstance(result, dict)
            assert 'error' in result
            assert isinstance(result['error'], str)
