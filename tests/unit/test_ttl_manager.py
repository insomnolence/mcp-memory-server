import pytest
import time
import math

from src.mcp_memory_server.memory.lifecycle import TTLManager, MemoryAging

# Fixture for TTLManager configuration


@pytest.fixture
def ttl_config():
    return {
        'high_frequency_base': 60,  # 1 minute
        'high_frequency_jitter': 10,
        'medium_frequency_base': 3600,  # 1 hour
        'medium_frequency_jitter': 600,
        'low_frequency_base': 86400,  # 1 day
        'low_frequency_jitter': 7200,
        'static_base': 604800,  # 1 week
        'static_jitter': 86400
    }

# Fixture for MemoryAging configuration


@pytest.fixture
def aging_config():
    return {
        'decay_rate': 0.1,  # 10% decay per day
        'minimum_score': 0.05,
        'enabled': True
    }

# Fixture for TTLManager instance


@pytest.fixture
def ttl_manager(ttl_config):
    return TTLManager(ttl_config)

# Fixture for MemoryAging instance


@pytest.fixture
def memory_aging(aging_config):
    return MemoryAging(aging_config)


class TestTTLManager:

    def test_calculate_ttl_high_frequency(self, ttl_manager):
        # Importance 0.1 (falls into high_frequency range 0.0-0.3)
        tier, ttl = ttl_manager.calculate_ttl(0.1)
        assert tier == 'high_frequency'
        assert ttl >= (60 - 10) and ttl <= (60 + 10)  # Base 60, Jitter 10

    def test_calculate_ttl_medium_frequency(self, ttl_manager):
        # Importance 0.4 (falls into medium_frequency range 0.3-0.5)
        tier, ttl = ttl_manager.calculate_ttl(0.4)
        assert tier == 'medium_frequency'
        assert ttl >= (3600 - 600) and ttl <= (3600 + 600)

    def test_calculate_ttl_low_frequency(self, ttl_manager):
        # Importance 0.6 (falls into low_frequency range 0.5-0.7)
        tier, ttl = ttl_manager.calculate_ttl(0.6)
        assert tier == 'low_frequency'
        assert ttl >= (86400 - 7200) and ttl <= (86400 + 7200)

    def test_calculate_ttl_static(self, ttl_manager):
        # Importance 0.8 (falls into static range 0.7-0.95)
        tier, ttl = ttl_manager.calculate_ttl(0.8)
        assert tier == 'static'
        assert ttl >= (604800 - 86400) and ttl <= (604800 + 86400)

    def test_calculate_ttl_permanent(self, ttl_manager):
        # Importance 0.98 (falls into permanent range 0.95-1.0)
        tier, ttl = ttl_manager.calculate_ttl(0.98)
        assert tier == 'permanent'
        assert ttl == float('inf')

    def test_calculate_ttl_access_multiplier(self, ttl_manager):
        # Test with high access count
        tier, ttl = ttl_manager.calculate_ttl(0.1, access_count=10)
        # Base 60 * (1.0 + (10-5)*0.1) = 60 * 1.5 = 90
        assert ttl >= (90 - 10) and ttl <= (90 + 10)

    def test_calculate_ttl_recency_multiplier(self, ttl_manager):
        current_time = time.time()
        # Recently accessed (within 1 day)
        tier, ttl_recent = ttl_manager.calculate_ttl(0.1, last_accessed=current_time - 3600)
        # Base 60 * 1.5 = 90
        assert ttl_recent >= (90 - 10) and ttl_recent <= (90 + 10)

        # Old access (more than 7 days ago)
        tier, ttl_old = ttl_manager.calculate_ttl(0.1, last_accessed=current_time - (86400 * 8))
        # Base 60 * 0.7 = 42, but minimum TTL is 60, so result should be 60
        assert ttl_old >= (60 - 10) and ttl_old <= (60 + 10)

    def test_should_expire(self, ttl_manager):
        current_time = time.time()
        # Document that should expire
        doc_expiring = {'ttl_expiry': current_time - 10, 'permanent_flag': False}
        assert ttl_manager.should_expire(doc_expiring) is True

        # Document that should not expire yet
        doc_not_expiring = {'ttl_expiry': current_time + 10, 'permanent_flag': False}
        assert ttl_manager.should_expire(doc_not_expiring) is False

        # Permanent document
        doc_permanent = {'ttl_expiry': current_time - 10, 'permanent_flag': True}
        assert ttl_manager.should_expire(doc_permanent) is False

        # Document in permanent tier
        doc_permanent_tier = {'ttl_expiry': current_time - 10, 'ttl_tier': 'permanent'}
        assert ttl_manager.should_expire(doc_permanent_tier) is False

    def test_add_ttl_metadata(self, ttl_manager):
        metadata = {'access_count': 5, 'timestamp': time.time() - 100}
        importance = 0.5
        updated_metadata = ttl_manager.add_ttl_metadata(metadata, importance)

        assert 'ttl_tier' in updated_metadata
        assert 'ttl_seconds' in updated_metadata
        assert 'ttl_expiry' in updated_metadata
        assert 'permanent_flag' in updated_metadata
        assert updated_metadata['permanent_flag'] is False

        # Test permanent flag addition
        metadata_perm = {'access_count': 1}
        importance_perm = 0.99
        updated_metadata_perm = ttl_manager.add_ttl_metadata(metadata_perm, importance_perm)
        assert updated_metadata_perm['permanent_flag'] is True
        assert updated_metadata_perm['ttl_expiry'] is None


class TestMemoryAging:

    def test_calculate_age_factor_new_document(self, memory_aging):
        current_time = time.time()
        # Document created now
        age_factor = memory_aging.calculate_age_factor(current_time, current_time)
        assert age_factor == pytest.approx(1.0)

    def test_calculate_age_factor_old_document(self, memory_aging):
        current_time = time.time()
        # Document 1 day old
        timestamp = current_time - 86400  # 1 day ago
        age_factor = memory_aging.calculate_age_factor(timestamp, current_time)
        expected_factor = math.exp(-memory_aging.decay_rate * 1)
        assert age_factor == pytest.approx(expected_factor)

    def test_calculate_age_factor_minimum_score(self, memory_aging):
        current_time = time.time()
        # Document very old, should hit minimum score
        timestamp = current_time - (86400 * 100)  # 100 days ago
        age_factor = memory_aging.calculate_age_factor(timestamp, current_time)
        assert age_factor == pytest.approx(memory_aging.minimum_score)

    def test_apply_aging_to_score(self, memory_aging):
        current_time = time.time()
        original_score = 0.8
        timestamp = current_time - 86400  # 1 day ago
        aged_score = memory_aging.apply_aging_to_score(original_score, timestamp, current_time)
        expected_score = original_score * math.exp(-memory_aging.decay_rate * 1)
        assert aged_score == pytest.approx(expected_score)

    def test_apply_aging_to_score_below_minimum(self, memory_aging):
        current_time = time.time()
        original_score = 0.01
        timestamp = current_time - 86400  # 1 day ago
        aged_score = memory_aging.apply_aging_to_score(original_score, timestamp, current_time)
        assert aged_score == pytest.approx(memory_aging.minimum_score * 0.5)

    def test_needs_score_refresh(self, memory_aging):
        current_time = time.time()
        # Needs refresh
        metadata_refresh = {'importance_scored_at': current_time - (86400 * 8)}
        assert memory_aging.needs_score_refresh(metadata_refresh) is True

        # Does not need refresh
        metadata_no_refresh = {'importance_scored_at': current_time - (86400 * 2)}
        assert memory_aging.needs_score_refresh(metadata_no_refresh) is False

        # Aging disabled
        memory_aging.aging_enabled = False
        assert memory_aging.needs_score_refresh(metadata_refresh) is False
