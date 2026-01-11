import pytest
from unittest.mock import Mock

from src.mcp_memory_server.memory.services.routing import QueryRoutingService


# Fixture for a mock deduplicator


@pytest.fixture
def mock_deduplicator():
    """Create a mock deduplicator with configurable behavior."""
    mock = Mock()
    mock.enabled = True
    mock.get_deduplication_stats.return_value = {
        'total_duplicates_removed': 10,
        'total_documents_processed': 100
    }
    return mock


@pytest.fixture
def mock_deduplicator_disabled():
    """Create a mock deduplicator that is disabled."""
    mock = Mock()
    mock.enabled = False
    return mock


@pytest.fixture
def mock_deduplicator_high_dedup_ratio():
    """Create a mock deduplicator with high deduplication ratio (>30%)."""
    mock = Mock()
    mock.enabled = True
    mock.get_deduplication_stats.return_value = {
        'total_duplicates_removed': 40,
        'total_documents_processed': 100
    }
    return mock


@pytest.fixture
def mock_deduplicator_empty_stats():
    """Create a mock deduplicator with empty stats."""
    mock = Mock()
    mock.enabled = True
    mock.get_deduplication_stats.return_value = {}
    return mock


# Fixture for QueryRoutingService


@pytest.fixture
def routing_service(mock_deduplicator):
    """Create a QueryRoutingService with default mock deduplicator."""
    return QueryRoutingService(deduplicator=mock_deduplicator)


@pytest.fixture
def routing_service_disabled_dedup(mock_deduplicator_disabled):
    """Create a QueryRoutingService with disabled deduplicator."""
    return QueryRoutingService(deduplicator=mock_deduplicator_disabled)


@pytest.fixture
def routing_service_high_dedup(mock_deduplicator_high_dedup_ratio):
    """Create a QueryRoutingService with high dedup ratio."""
    return QueryRoutingService(deduplicator=mock_deduplicator_high_dedup_ratio)


@pytest.fixture
def routing_service_with_config(mock_deduplicator):
    """Create a QueryRoutingService with custom config."""
    config = {'custom_setting': 'value'}
    return QueryRoutingService(deduplicator=mock_deduplicator, config=config)


class TestQueryRoutingServiceInit:

    def test_init_with_deduplicator(self, mock_deduplicator):
        service = QueryRoutingService(deduplicator=mock_deduplicator)
        assert service.deduplicator == mock_deduplicator
        assert service.config == {}

    def test_init_with_config(self, mock_deduplicator):
        config = {'threshold': 0.5, 'max_results': 10}
        service = QueryRoutingService(
            deduplicator=mock_deduplicator, config=config)
        assert service.config == config

    def test_init_with_none_config(self, mock_deduplicator):
        service = QueryRoutingService(
            deduplicator=mock_deduplicator, config=None)
        assert service.config == {}


class TestEstimateQueryImportance:

    def test_default_importance_is_medium(self, routing_service):
        """Basic query without special patterns should have medium importance."""
        importance = routing_service._estimate_query_importance("hello world")
        assert importance == pytest.approx(0.5)

    def test_technical_patterns_boost_importance(self, routing_service):
        """Queries with technical patterns should get +0.2 boost."""
        technical_queries = [
            "error in the system",
            "bug in login",
            "implementation details",
            "algorithm complexity",
            "function parameters",
            "class definition",
            "method signature"
        ]
        for query in technical_queries:
            importance = routing_service._estimate_query_importance(query)
            assert importance >= 0.7, f"Query '{query}' should have importance >= 0.7"

    def test_camel_case_boost_importance(self, routing_service):
        """Queries with camelCase identifiers should get +0.1 boost."""
        importance = routing_service._estimate_query_importance("getUserById")
        # Base 0.5 + camelCase 0.1 = 0.6
        assert importance >= 0.6

    def test_snake_case_boost_importance(self, routing_service):
        """Queries with snake_case identifiers should get +0.1 boost."""
        importance = routing_service._estimate_query_importance(
            "get_user_by_id")
        # Base 0.5 + snake_case 0.1 = 0.6
        assert importance >= 0.6

    def test_long_query_boost_importance(self, routing_service):
        """Queries with more than 5 words should get +0.1 boost."""
        short_query = "find user"
        long_query = "find the user who logged in yesterday morning"

        short_importance = routing_service._estimate_query_importance(
            short_query)
        long_importance = routing_service._estimate_query_importance(
            long_query)

        assert long_importance > short_importance
        assert long_importance >= 0.6  # Base 0.5 + long query 0.1

    def test_dedup_pattern_boost_importance(self, routing_service):
        """Queries matching dedup patterns should get +0.1 boost."""
        dedup_queries = [
            "config settings",
            "api endpoint",
            "test fixture",
            "mock data"
        ]
        for query in dedup_queries:
            importance = routing_service._estimate_query_importance(query)
            assert importance >= 0.6, f"Query '{query}' should have importance >= 0.6"

    def test_combined_boosts_cap_at_one(self, routing_service):
        """Multiple boosts should cap importance at 1.0."""
        # Technical + camelCase + long query + dedup pattern
        query = "implementation of getUserById function for api endpoint testing mock"
        importance = routing_service._estimate_query_importance(query)
        assert importance == pytest.approx(1.0)

    def test_high_importance_threshold(self, routing_service):
        """Query can reach high importance (>0.8) with multiple boosts."""
        # Technical (0.2) + camelCase (0.1) + long query (0.1) + dedup (0.1) =
        # 1.0
        query = "error in getUserData function implementation for api"
        importance = routing_service._estimate_query_importance(query)
        assert importance > 0.8

    def test_empty_query(self, routing_service):
        """Empty query should still return base importance."""
        importance = routing_service._estimate_query_importance("")
        assert importance == pytest.approx(0.5)

    def test_single_character_query(self, routing_service):
        """Single character query should return base importance."""
        importance = routing_service._estimate_query_importance("a")
        assert importance == pytest.approx(0.5)


class TestMatchesCommonDedupPatterns:

    def test_config_pattern(self, routing_service):
        assert routing_service._matches_common_dedup_patterns(
            "config file") is True
        assert routing_service._matches_common_dedup_patterns(
            "configuration") is True

    def test_setting_pattern(self, routing_service):
        assert routing_service._matches_common_dedup_patterns(
            "user settings") is True
        assert routing_service._matches_common_dedup_patterns(
            "SETTING value") is True

    def test_preference_pattern(self, routing_service):
        assert routing_service._matches_common_dedup_patterns(
            "user preference") is True

    def test_option_pattern(self, routing_service):
        assert routing_service._matches_common_dedup_patterns(
            "option value") is True
        assert routing_service._matches_common_dedup_patterns(
            "Optional parameter") is True

    def test_api_pattern(self, routing_service):
        assert routing_service._matches_common_dedup_patterns(
            "api call") is True
        assert routing_service._matches_common_dedup_patterns(
            "REST API") is True

    def test_endpoint_pattern(self, routing_service):
        assert routing_service._matches_common_dedup_patterns(
            "endpoint url") is True

    def test_request_response_patterns(self, routing_service):
        assert routing_service._matches_common_dedup_patterns(
            "http request") is True
        assert routing_service._matches_common_dedup_patterns(
            "json response") is True

    def test_test_patterns(self, routing_service):
        assert routing_service._matches_common_dedup_patterns(
            "test case") is True
        assert routing_service._matches_common_dedup_patterns(
            "unit spec") is True
        assert routing_service._matches_common_dedup_patterns(
            "mock object") is True
        assert routing_service._matches_common_dedup_patterns(
            "test fixture") is True

    def test_no_match(self, routing_service):
        assert routing_service._matches_common_dedup_patterns(
            "hello world") is False
        assert routing_service._matches_common_dedup_patterns(
            "random text") is False
        assert routing_service._matches_common_dedup_patterns("") is False

    def test_case_insensitive(self, routing_service):
        assert routing_service._matches_common_dedup_patterns("CONFIG") is True
        assert routing_service._matches_common_dedup_patterns("Api") is True
        assert routing_service._matches_common_dedup_patterns("TEST") is True


class TestAdjustKForDeduplication:

    def test_empty_stats_returns_original_k(self, routing_service):
        """Empty dedup stats should return original k."""
        result = routing_service._adjust_k_for_deduplication(10, {})
        assert result == 10

    def test_none_stats_returns_original_k(self, routing_service):
        """None-like empty stats should return original k."""
        result = routing_service._adjust_k_for_deduplication(10, {})
        assert result == 10

    def test_low_dedup_ratio_returns_original_k(self, routing_service):
        """Dedup ratio <= 30% should return original k."""
        stats = {
            'total_duplicates_removed': 20,
            'total_documents_processed': 100
        }
        result = routing_service._adjust_k_for_deduplication(10, stats)
        assert result == 10

    def test_high_dedup_ratio_adjusts_k(self, routing_service):
        """Dedup ratio > 30% should return max(k, int(k * 0.8))."""
        stats = {
            'total_duplicates_removed': 40,
            'total_documents_processed': 100
        }
        result = routing_service._adjust_k_for_deduplication(10, stats)
        # max(10, int(10 * 0.8)) = max(10, 8) = 10
        assert result == 10

    def test_high_dedup_ratio_with_large_k(self, routing_service):
        """High dedup ratio with large k should return adjusted value."""
        stats = {
            'total_duplicates_removed': 50,
            'total_documents_processed': 100
        }
        result = routing_service._adjust_k_for_deduplication(100, stats)
        # max(100, int(100 * 0.8)) = max(100, 80) = 100
        assert result == 100

    def test_boundary_dedup_ratio_exactly_30_percent(self, routing_service):
        """Exactly 30% dedup ratio should return original k."""
        stats = {
            'total_duplicates_removed': 30,
            'total_documents_processed': 100
        }
        result = routing_service._adjust_k_for_deduplication(10, stats)
        assert result == 10

    def test_boundary_dedup_ratio_just_over_30_percent(self, routing_service):
        """Just over 30% dedup ratio should adjust k."""
        stats = {
            'total_duplicates_removed': 31,
            'total_documents_processed': 100
        }
        result = routing_service._adjust_k_for_deduplication(10, stats)
        # max(10, 8) = 10
        assert result == 10

    def test_zero_documents_processed(self, routing_service):
        """Zero documents processed should handle division safely."""
        stats = {
            'total_duplicates_removed': 0,
            'total_documents_processed': 0
        }
        # total_processed defaults to 1 if 0
        result = routing_service._adjust_k_for_deduplication(10, stats)
        assert result == 10

    def test_missing_duplicates_removed_key(self, routing_service):
        """Missing total_duplicates_removed should default to 0."""
        stats = {
            'total_documents_processed': 100
        }
        result = routing_service._adjust_k_for_deduplication(10, stats)
        assert result == 10

    def test_missing_documents_processed_key(self, routing_service):
        """Missing total_documents_processed should default to 1."""
        stats = {
            'total_duplicates_removed': 50
        }
        result = routing_service._adjust_k_for_deduplication(10, stats)
        # 50/1 > 0.3, so adjustment applies
        # max(10, 8) = 10
        assert result == 10

    def test_k_of_one(self, routing_service):
        """k=1 should still work correctly."""
        stats = {
            'total_duplicates_removed': 50,
            'total_documents_processed': 100
        }
        result = routing_service._adjust_k_for_deduplication(1, stats)
        # max(1, int(1 * 0.8)) = max(1, 0) = 1
        assert result == 1

    def test_k_of_zero(self, routing_service):
        """k=0 should return 0."""
        stats = {
            'total_duplicates_removed': 50,
            'total_documents_processed': 100
        }
        result = routing_service._adjust_k_for_deduplication(0, stats)
        assert result == 0


class TestSmartQueryRouting:

    def test_high_importance_query_routes_to_long_term_first(
            self, routing_service):
        """High importance queries (>0.8) should route to long_term first."""
        # Create a query with high importance
        query = "error in getUserData function implementation for api endpoint"
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=10)

        assert search_order == ['long_term', 'short_term']
        assert collection_limits[0] == 10 // 2 + 1  # 6
        assert collection_limits[1] == 10 // 2  # 5

    def test_medium_importance_query_routes_to_short_term_first(
            self, routing_service):
        """Medium importance queries (0.5-0.8) should route to short_term first with balanced limits."""
        query = "find something specific"  # camelCase or snake_case gives +0.1
        query = "find_something"  # snake_case gives 0.5 + 0.1 = 0.6

        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=10)

        assert search_order == ['short_term', 'long_term']
        assert collection_limits[0] == 10 // 2  # 5
        assert collection_limits[1] == 10 // 2  # 5

    def test_low_importance_query_routes_to_short_term_first(
            self, routing_service):
        """Low importance queries (<=0.5) should route to short_term first."""
        query = "hello"

        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=10)

        assert search_order == ['short_term', 'long_term']
        assert collection_limits[0] == 10 // 2 + 1  # 6
        assert collection_limits[1] == 10 // 2  # 5

    def test_routing_with_disabled_deduplicator(
            self, routing_service_disabled_dedup):
        """Routing should work when deduplicator is disabled."""
        query = "hello world"
        search_order, collection_limits, effective_k = routing_service_disabled_dedup.smart_query_routing(
            query, k=10)

        assert search_order in [
            ['short_term', 'long_term'], ['long_term', 'short_term']]
        assert effective_k == 10

    def test_routing_calls_deduplicator_get_stats(
            self, routing_service, mock_deduplicator):
        """Routing should call deduplicator.get_deduplication_stats when enabled."""
        query = "test query"
        routing_service.smart_query_routing(query, k=10)

        mock_deduplicator.get_deduplication_stats.assert_called_once()

    def test_effective_k_with_high_dedup_ratio(
            self, routing_service_high_dedup):
        """Effective k should be adjusted when dedup ratio is high."""
        query = "hello world"
        search_order, collection_limits, effective_k = routing_service_high_dedup.smart_query_routing(
            query, k=10)

        # With high dedup ratio (40%), effective_k = max(10, int(10 * 0.8)) =
        # 10
        assert effective_k == 10

    def test_odd_k_value_distribution(self, routing_service):
        """Test that odd k values are distributed correctly."""
        query = "hello"  # Low importance
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=11)

        # Low importance: [k//2 + 1, k//2] = [6, 5]
        assert collection_limits[0] == 6
        assert collection_limits[1] == 5

    def test_k_of_one(self, routing_service):
        """Test routing with k=1."""
        query = "hello"
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=1)

        assert effective_k == 1
        # 1//2 + 1 = 1, 1//2 = 0
        assert collection_limits[0] == 1
        assert collection_limits[1] == 0

    def test_k_of_two(self, routing_service):
        """Test routing with k=2."""
        query = "hello"
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=2)

        assert effective_k == 2
        # 2//2 + 1 = 2, 2//2 = 1
        assert collection_limits[0] == 2
        assert collection_limits[1] == 1

    def test_large_k_value(self, routing_service):
        """Test routing with large k value."""
        query = "hello"
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=1000)

        assert effective_k == 1000
        assert collection_limits[0] == 501  # 1000//2 + 1
        assert collection_limits[1] == 500  # 1000//2

    def test_returns_tuple_of_correct_types(self, routing_service):
        """Test that return value is a tuple with correct types."""
        query = "test"
        result = routing_service.smart_query_routing(query, k=10)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], list)  # search_order
        assert isinstance(result[1], list)  # collection_limits
        assert isinstance(result[2], int)   # effective_k

    def test_search_order_contains_both_collections(self, routing_service):
        """Test that search_order always contains both collection names."""
        queries = ["hello", "error in implementation", "find_user"]

        for query in queries:
            search_order, _, _ = routing_service.smart_query_routing(
                query, k=10)
            assert 'short_term' in search_order
            assert 'long_term' in search_order
            assert len(search_order) == 2


class TestSmartQueryRoutingEdgeCases:

    def test_empty_query(self, routing_service):
        """Test routing with empty query."""
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            "", k=10)

        # Empty query has base importance 0.5, which is <=0.5, so low
        # importance path
        assert search_order == ['short_term', 'long_term']
        assert effective_k == 10

    def test_whitespace_only_query(self, routing_service):
        """Test routing with whitespace-only query."""
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            "   ", k=10)

        assert search_order in [
            ['short_term', 'long_term'], ['long_term', 'short_term']]
        assert effective_k == 10

    def test_special_characters_query(self, routing_service):
        """Test routing with special characters in query."""
        query = "!@#$%^&*()"
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=10)

        assert effective_k == 10
        assert len(search_order) == 2

    def test_unicode_query(self, routing_service):
        """Test routing with unicode characters."""
        query = "find in database"
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=10)

        assert effective_k == 10
        assert len(search_order) == 2

    def test_very_long_query(self, routing_service):
        """Test routing with very long query."""
        query = "word " * 100  # 100 words
        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=10)

        # Long query (>5 words) should boost importance
        assert effective_k == 10
        assert len(search_order) == 2


class TestSmartQueryRoutingWithoutDeduplicatorAttribute:

    def test_routing_without_deduplicator_attribute(self):
        """Test that routing works even if deduplicator attribute doesn't exist."""
        # Create service without proper deduplicator
        service = QueryRoutingService(deduplicator=None, config={})

        # Should not raise error, should handle gracefully
        search_order, collection_limits, effective_k = service.smart_query_routing(
            "test", k=10)

        assert effective_k == 10
        assert len(search_order) == 2


class TestQueryRoutingServiceIntegration:

    def test_full_routing_flow_high_importance(self, routing_service):
        """Test complete routing flow for high importance query."""
        # High importance: technical term + identifier + dedup pattern + long
        # query
        query = "error in getUserById function implementation for api endpoint"

        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=20)

        # Should route to long_term first
        assert search_order[0] == 'long_term'
        # Limits should favor long_term
        assert collection_limits[0] > collection_limits[1]
        assert sum(collection_limits) >= effective_k - \
            1  # Allow for integer division

    def test_full_routing_flow_low_importance(self, routing_service):
        """Test complete routing flow for low importance query."""
        query = "hello"

        search_order, collection_limits, effective_k = routing_service.smart_query_routing(
            query, k=20)

        # Should route to short_term first
        assert search_order[0] == 'short_term'
        # Limits should favor short_term
        assert collection_limits[0] > collection_limits[1]

    def test_importance_affects_routing_decision(self, routing_service):
        """Test that different importance levels lead to different routing."""
        low_importance_query = "hi"
        high_importance_query = "error in getUserById implementation for api"

        low_result = routing_service.smart_query_routing(
            low_importance_query, k=10)
        high_result = routing_service.smart_query_routing(
            high_importance_query, k=10)

        # High importance should route to long_term first
        assert high_result[0][0] == 'long_term'
        # Low importance should route to short_term first
        assert low_result[0][0] == 'short_term'
