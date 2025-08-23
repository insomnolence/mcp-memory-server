import pytest
import math
import time
from unittest.mock import Mock

from src.mcp_memory_server.memory.scorer import MemoryImportanceScorer, DomainPatternEngine

# Fixture for a basic scoring configuration
@pytest.fixture
def basic_scoring_config():
    return {
        'decay_constant': 86400, # 1 day
        'max_access_count': 100,
        'scoring_weights': {
            'semantic': 0.4,
            'recency': 0.3,
            'frequency': 0.2,
            'importance': 0.1
        },
        'base_scoring': {
            'length_normalization': 1000,
            'max_length_score': 0.5 # Max 0.5 from content length
        },
        'domain_patterns': {
            'patterns': {
                'code_pattern': {'keywords': ['def', 'class'], 'bonus': 0.2},
                'error_pattern': {'keywords': ['error', 'exception'], 'bonus': 0.3}
            },
            'permanence_triggers': {
                'critical_keyword': {'keywords': ['critical'], 'boost': 0.5},
                'critical_flag': {'boost': 0.5}  # For metadata-based matching
            }
        }
    }

# Fixture for MemoryImportanceScorer
@pytest.fixture
def importance_scorer(basic_scoring_config):
    return MemoryImportanceScorer(basic_scoring_config)


class TestDomainPatternEngine:

    def test_analyze_content_keywords(self):
        config = {
            'patterns': {
                'test_pattern': {'keywords': ['apple', 'banana'], 'bonus': 0.5}
            }
        }
        engine = DomainPatternEngine(config)
        assert engine.analyze_content("I like apple and orange") == {'test_pattern': 0.5}
        assert engine.analyze_content("I like banana") == {'test_pattern': 0.5}
        assert engine.analyze_content("I like grapes") == {}

    def test_analyze_content_regex(self):
        config = {
            'patterns': {
                'regex_pattern': {'regex_patterns': [r'[0-9]{3}-\d{2}-\d{4}'], 'bonus': 0.7}
            }
        }
        engine = DomainPatternEngine(config)
        assert engine.analyze_content("My SSN is 123-45-6789") == {'regex_pattern': 0.7}
        assert engine.analyze_content("My phone is 123-456-7890") == {}

    def test_analyze_content_match_mode_all(self):
        config = {
            'patterns': {
                'all_pattern': {'keywords': ['cat', 'dog'], 'bonus': 0.6, 'match_mode': 'all'}
            }
        }
        engine = DomainPatternEngine(config)
        assert engine.analyze_content("The cat and the dog") == {'all_pattern': 0.6}
        assert engine.analyze_content("Only the cat") == {}

    def test_analyze_content_match_mode_weighted(self):
        config = {
            'patterns': {
                'weighted_pattern': {'keywords': ['one', 'two', 'three'], 'bonus': 1.0, 'match_mode': 'weighted'}
            }
        }
        engine = DomainPatternEngine(config)
        assert engine.analyze_content("This has one and two") == {'weighted_pattern': pytest.approx(2/3 * 1.0)}
        assert engine.analyze_content("This has one") == {'weighted_pattern': pytest.approx(1/3 * 1.0)}

    def test_analyze_permanence(self):
        config = {
            'permanence_triggers': {
                'important_keyword': {'keywords': ['critical'], 'boost': 0.5},
                'type_flag': {'boost': 0.3},
                'critical_flag': {'boost': 0.5}  # Add the flag that the test expects
            }
        }
        engine = DomainPatternEngine(config)
        assert engine.analyze_permanence("This is critical information") == 0.5
        assert engine.analyze_permanence("Normal content") == 0.0
        assert engine.analyze_permanence("", metadata={'permanence_flag': 'critical_flag'}) == 0.5 # Test metadata flag

    def test_invalid_pattern_config_handling(self):
        # Test with a pattern missing 'keywords' or 'regex_patterns'
        config_missing_keys = {
            'patterns': {
                'invalid_pattern': {'bonus': 0.5}
            }
        }
        engine_missing_keys = DomainPatternEngine(config_missing_keys)
        # Should not raise an error, but also not match anything
        assert engine_missing_keys.analyze_content("some content") == {}

        # Test with a pattern where 'bonus' is not a number
        config_bad_bonus = {
            'patterns': {
                'bad_bonus_pattern': {'keywords': ['test'], 'bonus': 'not_a_number'}
            }
        }
        engine_bad_bonus = DomainPatternEngine(config_bad_bonus)
        # Should not raise an error, but also not match anything
        assert engine_bad_bonus.analyze_content("test content") == {}

        # Test with malformed regex
        config_malformed_regex = {
            'patterns': {
                'malformed_regex_pattern': {'regex_patterns': ['['], 'bonus': 0.1}
            }
        }
        engine_malformed_regex = DomainPatternEngine(config_malformed_regex)
        # Should not raise an error, but also not match anything
        assert engine_malformed_regex.analyze_content("content") == {}


class TestMemoryImportanceScorer:

    def test_calculate_importance_base_content_length(self, importance_scorer):
        # Content length directly contributes: length/normalization_factor
        content = "a" * 500 # 500/1000 = 0.5
        score = importance_scorer.calculate_importance(content)
        assert score == pytest.approx(0.5) # Direct length score: 500/1000 = 0.5

    def test_calculate_importance_with_domain_patterns(self, importance_scorer):
        content = "This code defines a new class and handles an exception."
        # Expected: content_length/1000 + pattern bonuses
        # Content length = 55, so 55/1000 = 0.055
        # code_pattern bonus 0.2, error_pattern bonus 0.3
        score = importance_scorer.calculate_importance(content)
        expected_score = len(content) / 1000 + 0.2 + 0.3  # 0.055 + 0.2 + 0.3 = 0.555
        assert score == pytest.approx(expected_score)

    def test_calculate_importance_with_permanence_boost(self, importance_scorer):
        content = "This is critical system configuration."
        metadata = {'permanence_flag': 'critical_flag'}
        # Expected: content_length/1000 + permanence boost from critical_keyword + permanence boost from critical_flag
        # Content length = 38, so 38/1000 = 0.038
        # critical keyword detected = +0.5 (from 'critical' in content)
        # critical_flag metadata = +0.5 (from permanence_flag)
        # Total = 0.038 + 0.5 + 0.5 = 1.038, capped at 1.0
        score = importance_scorer.calculate_importance(content, metadata=metadata)
        assert score == pytest.approx(1.0)

    def test_calculate_importance_context_permanence_requested(self, importance_scorer):
        content = "Important solution for a bug."
        context = {'permanence_requested': True}
        # Expected: content_length/1000 + context permanence boost (0.25)
        # Content length = 29, so 29/1000 = 0.029
        # Context permanence boost = 0.25
        # Total = 0.029 + 0.25 = 0.279
        score = importance_scorer.calculate_importance(content, context=context)
        expected_score = len(content) / 1000 + 0.25  # 0.029 + 0.25 = 0.279
        assert score == pytest.approx(expected_score)

    def test_calculate_importance_caps_at_one(self, importance_scorer):
        # Create a new config to test capping behavior
        config = {
            'base_scoring': {
                'length_normalization': 1000,
                'max_length_score': 1.0
            },
            'domain_patterns': {
                'patterns': {
                    'high_bonus_1': {'keywords': ['a'], 'bonus': 0.5},
                    'high_bonus_2': {'keywords': ['b'], 'bonus': 0.5}, 
                    'high_bonus_3': {'keywords': ['c'], 'bonus': 0.5}
                }
            }
        }
        scorer = MemoryImportanceScorer(config)
        content = "a b c" * 1000 # Very long content to max out length score
        score = scorer.calculate_importance(content)
        # Score should be capped at 1.0 regardless of individual components
        assert score == pytest.approx(1.0)

    def test_calculate_retrieval_score(self, importance_scorer):
        memory_data = {
            'metadata': {
                'timestamp': time.time() - 86400, # 1 day old
                'access_count': 10,
                'importance_score': 0.8
            },
            'distance': 0.1 # High semantic similarity
        }
        query = "test query"
        current_time = time.time()

        # Expected calculation based on weights:
        # semantic: 1.0 - 0.1 = 0.9
        # recency: exp(-1 day / 1 day) = exp(-1) = 0.3678
        # frequency: min(10/100, 1.0) = 0.1
        # importance: 0.8
        # total = 0.9*0.4 + 0.3678*0.3 + 0.1*0.2 + 0.8*0.1
        #       = 0.36 + 0.11034 + 0.02 + 0.08 = 0.57034
        expected_score = (
            (1.0 - memory_data['distance']) * importance_scorer.scoring_weights['semantic'] +
            math.exp(-(current_time - memory_data['metadata']['timestamp']) / importance_scorer.decay_constant) * importance_scorer.scoring_weights['recency'] +
            min(memory_data['metadata']['access_count'] / importance_scorer.max_access_count, 1.0) * importance_scorer.scoring_weights['frequency'] +
            memory_data['metadata']['importance_score'] * importance_scorer.scoring_weights['importance']
        )

        score = importance_scorer.calculate_retrieval_score(memory_data, query, current_time)
        assert score == pytest.approx(expected_score)

    def test_scorer_attributes_accessible(self, importance_scorer):
        """Test that scorer configuration attributes are accessible."""
        assert hasattr(importance_scorer, 'decay_constant')
        assert hasattr(importance_scorer, 'scoring_weights')
        assert hasattr(importance_scorer, 'pattern_engine')
        assert importance_scorer.decay_constant > 0

    def test_calculate_importance_empty_content(self, importance_scorer):
        score = importance_scorer.calculate_importance("")
        assert score == pytest.approx(0.0) # Empty content should yield 0 importance

    def test_calculate_importance_missing_metadata_context(self, importance_scorer):
        # Should not raise an error, should use defaults
        score = importance_scorer.calculate_importance("some content", metadata=None, context=None)
        assert score > 0.0 # Should still get some score from content length

    def test_calculate_retrieval_score_missing_metadata_keys(self, importance_scorer):
        memory_data_incomplete = {
            'metadata': {},
            'distance': 0.5
        }
        query = "test query"
        current_time = time.time()

        # Should not raise an error, should use defaults for missing metadata keys
        score = importance_scorer.calculate_retrieval_score(memory_data_incomplete, query, current_time)
        assert score >= 0.0

    def test_calculate_retrieval_score_no_distance(self, importance_scorer):
        memory_data_no_distance = {
            'metadata': {
                'timestamp': time.time(),
                'access_count': 1,
                'importance_score': 0.5
            }
        }
        query = "test query"
        current_time = time.time()

        # Should not raise an error, semantic score should default or be handled
        score = importance_scorer.calculate_retrieval_score(memory_data_no_distance, query, current_time)
        assert score >= 0.0
