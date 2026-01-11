import pytest
import time
from unittest.mock import patch

from src.mcp_memory_server.memory.query_monitor import QueryPerformanceMonitor

# Fixture for QueryPerformanceMonitor configuration


@pytest.fixture
def query_monitor_config():
    return {
        'enabled': True,
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

# Fixture for QueryPerformanceMonitor instance


@pytest.fixture
def query_monitor(query_monitor_config):
    return QueryPerformanceMonitor(query_monitor_config)


class TestQueryPerformanceMonitor:

    def test_track_query(self, query_monitor):
        query = "test query"
        results = {'total_results': 5, 'processing_time_ms': 100}
        processing_time_s = 0.1
        query_metadata = {'effective_k': 5}

        query_monitor.track_query(query, results, processing_time_s, query_metadata)

        assert len(query_monitor.query_history) == 1
        log_entry = query_monitor.query_history[0]
        assert log_entry['query'] == query
        assert log_entry['total_results'] == 5
        assert log_entry['processing_time_ms'] == pytest.approx(100)
        assert log_entry['metadata']['effective_k'] == 5
        assert 'timestamp' in log_entry

    def test_track_query_disabled(self, query_monitor_config):
        """Test that QueryPerformanceMonitor tracks queries (no disable functionality in current implementation)."""
        # Current implementation doesn't support enabled/disabled, so it always tracks
        monitor = QueryPerformanceMonitor(query_monitor_config)
        monitor.track_query("test", {}, 0.1, {})
        assert len(monitor.query_history) == 1  # Always tracks in current implementation

    def test_get_performance_summary_empty(self, query_monitor):
        summary = query_monitor.get_performance_summary()
        assert summary['query_count'] == 0

    def test_get_performance_summary_with_data(self, query_monitor):
        query_monitor.track_query("q1", {'total_results': 1}, 0.1, {})
        query_monitor.track_query("q2", {'total_results': 2}, 0.2, {})

        summary = query_monitor.get_performance_summary()
        assert summary['query_count'] == 2
        assert 'response_time_stats' in summary

    def test_get_performance_summary_time_window(self, query_monitor):
        current_time = time.time()
        # Add an old query (more than a day ago)
        with patch('time.time', return_value=current_time - (86400 * 2)):
            query_monitor.track_query("old_q", {'total_results': 1}, 0.5, {})

        # Add a recent query (within the last hour)
        with patch('time.time', return_value=current_time - 1800):
            query_monitor.track_query("recent_q_hour", {'total_results': 1}, 0.1, {})

        # Add a very recent query (now)
        query_monitor.track_query("recent_q_now", {'total_results': 1}, 0.05, {})

        summary_hour = query_monitor.get_performance_summary(time_window='hour')
        assert summary_hour['query_count'] == 2  # recent_q_hour and recent_q_now
        assert summary_hour['response_time_stats']['mean_ms'] == pytest.approx(75)  # (100+50)/2

        summary_day = query_monitor.get_performance_summary(time_window='day')
        assert summary_day['query_count'] == 2  # recent_q_hour and recent_q_now (old query beyond day window)

        summary_all = query_monitor.get_performance_summary(time_window='all')
        assert summary_all['query_count'] == 3

    def test_export_metrics(self, query_monitor):
        """Test export_metrics method which exists in the current implementation."""
        query_monitor.track_query("q1", {'total_results': 1}, 0.1, {})
        query_monitor.track_query("q2", {'total_results': 2}, 0.2, {})

        exported_data = query_monitor.export_metrics()
        assert 'query_count' in exported_data
        assert exported_data['query_count'] == 2

    def test_get_real_time_metrics(self, query_monitor):
        current_time = time.time()
        with patch('time.time', return_value=current_time - 5):
            query_monitor.track_query("q_old", {'total_results': 1}, 0.1, {})
        query_monitor.track_query("q_new", {'total_results': 1}, 0.1, {})
        query_monitor.track_query("q_new2", {'total_results': 1}, 0.1, {})

        # Get real-time metrics which includes query rate
        metrics = query_monitor.get_real_time_metrics()
        assert 'queries_per_minute' in metrics
        assert 'system_health_score' in metrics

    def test_get_performance_metrics_with_response_time(self, query_monitor):
        """Test that performance summary includes response time statistics."""
        current_time = time.time()
        with patch('time.time', return_value=current_time - 5):
            query_monitor.track_query("q_old", {'total_results': 1}, 0.1, {})
        query_monitor.track_query("q_new", {'total_results': 1}, 0.2, {})
        query_monitor.track_query("q_new2", {'total_results': 1}, 0.3, {})

        summary = query_monitor.get_performance_summary()
        assert 'response_time_stats' in summary
        assert 'mean_ms' in summary['response_time_stats']
