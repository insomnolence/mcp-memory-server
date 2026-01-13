import time
import math
import re
from typing import Any, Dict, Optional


class DomainPatternEngine:
    """Domain pattern matching engine for flexible content analysis."""

    def __init__(self, pattern_config: dict):
        """Initialize pattern engine with user-defined patterns.

        Args:
            pattern_config: Configuration dict containing pattern definitions
        """
        self.patterns = pattern_config.get('patterns', {})
        self.permanence_triggers = pattern_config.get('permanence_triggers', {})
        self.case_sensitive = pattern_config.get('case_sensitive', False)

    def analyze_content(self, content: str) -> Dict[str, float]:
        """Analyze content against all defined patterns.

        Args:
            content: The text content to analyze

        Returns:
            Dict mapping pattern names to their bonus scores
        """
        results = {}
        search_content = content if self.case_sensitive else content.lower()

        # Check all defined patterns (skip comment entries)
        for pattern_name, pattern_config in self.patterns.items():
            if pattern_name.startswith('_comment'):
                continue  # Skip comment entries
            if not isinstance(pattern_config, dict):
                continue  # Skip non-dict entries
            bonus = self._check_pattern(search_content, pattern_config)
            if bonus > 0:
                results[pattern_name] = bonus

        return results

    def analyze_permanence(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> float:
        """Analyze content for permanence triggers.

        Args:
            content: The text content to analyze
            metadata: Optional metadata dictionary

        Returns:
            Total permanence boost score
        """
        if metadata is None:
            metadata = {}

        total_boost = 0.0
        search_content = content if self.case_sensitive else content.lower()

        # Check for permanence triggers in content (skip comment entries)
        for trigger_name, trigger_config in self.permanence_triggers.items():
            if trigger_name.startswith('_comment'):
                continue  # Skip comment entries
            if not isinstance(trigger_config, dict):
                continue  # Skip non-dict entries
            if self._check_pattern_boolean(search_content, trigger_config):
                total_boost += trigger_config.get('boost', 0.0)

        # Check for explicit permanence requests in metadata
        content_type = metadata.get('type', '')
        if content_type in self.permanence_triggers:
            total_boost += self.permanence_triggers[content_type].get('boost', 0.0)

        # Check for permanence flag
        permanence_flag = metadata.get('permanence_flag')
        if permanence_flag and permanence_flag in self.permanence_triggers:
            total_boost += self.permanence_triggers[permanence_flag].get('boost', 0.0)

        return min(total_boost, 1.0)  # Cap at 1.0

    def _check_pattern(self, content: str, pattern_config: dict) -> float:
        """Check if content matches a pattern configuration.

        Args:
            content: The content to check (already case-processed)
            pattern_config: Pattern configuration dict

        Returns:
            Bonus score if pattern matches, 0.0 otherwise
        """
        keywords = pattern_config.get('keywords', [])
        patterns = pattern_config.get('regex_patterns', [])
        bonus = pattern_config.get('bonus', pattern_config.get('boost', 0.0))  # Try 'bonus' first, then 'boost'

        # Validate bonus is a number
        if not isinstance(bonus, (int, float)):
            return 0.0
        match_mode = pattern_config.get('match_mode', 'any')  # 'any', 'all', 'weighted'

        matches = []

        # Check keyword matches
        for keyword in keywords:
            search_keyword = keyword if self.case_sensitive else keyword.lower()
            if search_keyword in content:
                matches.append(True)
            else:
                matches.append(False)

        # Check regex pattern matches
        for pattern in patterns:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                if re.search(pattern, content, flags):
                    matches.append(True)
                else:
                    matches.append(False)
            except re.error:
                # Invalid regex, skip
                matches.append(False)

        # Apply matching logic
        if not matches:
            return 0.0

        if match_mode == 'all':
            return bonus if all(matches) else 0.0
        elif match_mode == 'weighted':
            # Return proportional bonus based on match percentage
            match_ratio = sum(matches) / len(matches)
            return bonus * match_ratio
        else:  # 'any' (default)
            return bonus if any(matches) else 0.0

    def _check_pattern_boolean(self, content: str, pattern_config: dict) -> bool:
        """Check if content matches a pattern (boolean result)."""
        return self._check_pattern(content, pattern_config) > 0.0


class MemoryImportanceScorer:
    """Universal memory importance scoring system with configurable pattern matching."""

    def __init__(self, scoring_config: dict):
        """Initialize scorer with configuration parameters.

        Args:
            scoring_config: Configuration dict containing scoring parameters
        """
        self.decay_constant = scoring_config.get('decay_constant', 86400)
        self.max_access_count = scoring_config.get('max_access_count', 100)
        self.scoring_weights = scoring_config.get('scoring_weights', {
            'semantic': 0.4,
            'recency': 0.3,
            'frequency': 0.2,
            'importance': 0.1
        })

        # Initialize domain pattern engine
        pattern_config = scoring_config.get('domain_patterns', {})
        self.pattern_engine = DomainPatternEngine(pattern_config)

        # Base content scoring factors
        self.base_scoring = scoring_config.get('base_scoring', {
            'length_normalization': 1000,  # Normalize content length by this value
            'max_length_score': 1.0        # Maximum score from length alone
        })

        # Legacy support for old hardcoded patterns (backward compatibility)
        self.legacy_content_scoring = scoring_config.get('content_scoring')
        self.legacy_permanence_factors = scoring_config.get('permanence_factors')

    def calculate_importance(self, content: str, metadata: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> float:
        """Calculate importance score for new memory entries.

        Args:
            content: The text content to score
            metadata: Optional metadata dictionary
            context: Optional context dictionary with importance hints

        Returns:
            Float importance score between 0.0 and 1.0
        """
        if metadata is None:
            metadata = {}

        # Base content score (normalized by length)
        content_length = len(content)
        length_norm = self.base_scoring['length_normalization']
        max_length_score = self.base_scoring['max_length_score']
        content_score = min(content_length / length_norm, max_length_score)

        # Domain pattern-based scoring
        pattern_bonuses = self.pattern_engine.analyze_content(content)
        total_pattern_bonus = sum(pattern_bonuses.values())

        # Context-based scoring from domain patterns
        context_bonus = 0
        if context:
            # Check if context indicates any pattern categories
            for key, value in context.items():
                if value and key in self.pattern_engine.patterns:
                    context_bonus += self.pattern_engine.patterns[key].get('bonus', 0)

        # Permanence boost analysis
        permanence_boost = self.pattern_engine.analyze_permanence(content, metadata)

        # Handle legacy context permanence request
        if context and context.get('permanence_requested', False):
            permanence_boost += 0.25  # Default user explicit permanent boost

        # Legacy backward compatibility
        legacy_bonus: float = 0.0
        if self.legacy_content_scoring:
            legacy_bonus = self._calculate_legacy_bonus(content, metadata, context)

        # Combine all scoring factors
        total_score: float = content_score + total_pattern_bonus + context_bonus + permanence_boost + legacy_bonus

        # Respect explicit non-importance signal from caller
        # When is_important is explicitly False, cap score below permanent tier (0.95+)
        # This ensures checkpoints and ephemeral content don't become permanent
        if context and context.get('is_important') is False:
            total_score = min(total_score, 0.94)

        return float(min(1.0, total_score))

    def _calculate_legacy_bonus(self, content: str, metadata: Optional[Dict[str, Any]], context: Optional[Dict[str, Any]]) -> float:
        """Calculate legacy bonus scores for backward compatibility.

        Args:
            content: The text content to score
            metadata: Optional metadata dictionary
            context: Optional context dictionary

        Returns:
            Legacy bonus score
        """
        if not self.legacy_content_scoring:
            return 0.0

        legacy_bonus = 0
        content_lower = content.lower()

        # Legacy hardcoded pattern detection
        has_code = any(keyword in content_lower for keyword in ['def ', 'class ', 'function', 'import', 'return'])
        has_error = any(keyword in content_lower for keyword in ['error', 'exception', 'failed', 'bug'])

        # Apply legacy bonuses
        if has_code:
            legacy_bonus += self.legacy_content_scoring.get('code_bonus', 0)
        if has_error:
            legacy_bonus += self.legacy_content_scoring.get('error_bonus', 0)

        # Context-based legacy scoring
        if context:
            is_solution = context.get('is_solution', False)
            is_important = context.get('is_important', False)
            if is_solution:
                legacy_bonus += self.legacy_content_scoring.get('solution_bonus', 0)
            if is_important:
                legacy_bonus += self.legacy_content_scoring.get('important_bonus', 0)

        # Language importance
        if metadata:
            language = metadata.get('language', 'text')
            if language != 'text':
                legacy_bonus += self.legacy_content_scoring.get('language_bonus', 0)

        # Legacy permanence factors
        if self.legacy_permanence_factors and metadata:
            content_type = metadata.get('type', '')
            if content_type in self.legacy_permanence_factors:
                legacy_bonus += self.legacy_permanence_factors[content_type]

            permanence_flag = metadata.get('permanence_flag')
            if permanence_flag == 'critical':
                legacy_bonus += self.legacy_permanence_factors.get('user_explicit_permanent', 0.25)

        return legacy_bonus

    def calculate_retrieval_score(self, memory_data: Dict[str, Any], query: str, current_time: Optional[float] = None) -> float:
        """Calculate dynamic retrieval score for existing memories.

        Args:
            memory_data: Dictionary containing memory document and metadata
            query: The search query being performed
            current_time: Current timestamp (defaults to current time)

        Returns:
            Float retrieval score for ranking results
        """
        if current_time is None:
            current_time = time.time()

        metadata = memory_data.get('metadata', {})

        # Semantic similarity (from ChromaDB distance - lower is better)
        distance = memory_data.get('distance', 1.0)
        semantic_score = 1.0 - min(distance, 1.0)  # Convert distance to similarity

        # Recency score
        timestamp = metadata.get('timestamp', current_time)
        time_delta = current_time - timestamp
        recency_score = math.exp(-time_delta / self.decay_constant)

        # Frequency score
        access_count = metadata.get('access_count', 0)
        frequency_score = min(access_count / self.max_access_count, 1.0)

        # Importance score from metadata
        importance_score = metadata.get('importance_score', 0.5)

        # Weighted combination
        total_score = (
            semantic_score * self.scoring_weights['semantic'] +
            recency_score * self.scoring_weights['recency'] +
            frequency_score * self.scoring_weights['frequency'] +
            importance_score * self.scoring_weights['importance']
        )

        return float(total_score)
