"""
Query Routing Service

Handles intelligent query routing decisions including:
- Smart collection selection based on query importance
- Deduplication-aware routing optimization
- Search parameter adjustment
"""

from typing import Dict, Any, List, Tuple, Optional


class QueryRoutingService:
    """Service responsible for smart query routing decisions."""

    def __init__(self, deduplicator: Any, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize routing service.

        Args:
            deduplicator: MemoryDeduplicator instance for dedup-aware routing
            config: Configuration dictionary
        """
        self.deduplicator = deduplicator
        self.config = config or {}

    def smart_query_routing(self, query: str, k: int) -> Tuple[List[str], List[int], int]:
        """Deduplication-aware smart query routing.

        Args:
            query: The search query
            k: Number of results requested

        Returns:
            Tuple of (search_order, collection_limits, effective_k)
        """
        # Estimate query importance
        query_importance = self._estimate_query_importance(query)

        # Get deduplication statistics for routing decisions
        dedup_stats = {}
        if hasattr(self, 'deduplicator') and self.deduplicator and self.deduplicator.enabled:
            dedup_stats = self.deduplicator.get_deduplication_stats()

        # Adjust k based on deduplication effectiveness
        effective_k = self._adjust_k_for_deduplication(k, dedup_stats)

        # Route based on importance and deduplication quality
        if query_importance > 0.8:
            # High-importance: long-term has higher quality post-deduplication
            search_order = ['long_term', 'short_term']
            collection_limits = [effective_k // 2 + 1, effective_k // 2]
        elif query_importance > 0.5:
            # Medium-importance: balanced approach
            search_order = ['short_term', 'long_term']
            collection_limits = [effective_k // 2, effective_k // 2]
        else:
            # Low-importance: short-term first, but with deduplication benefits
            search_order = ['short_term', 'long_term']
            collection_limits = [effective_k // 2 + 1, effective_k // 2]

        return search_order, collection_limits, effective_k

    def _estimate_query_importance(self, query: str) -> float:
        """Estimate query importance based on content patterns.

        Args:
            query: The search query

        Returns:
            Estimated importance score (0.0-1.0)
        """
        # Basic importance estimation
        importance = 0.5  # Default medium importance

        # Boost for technical/specific terms
        technical_patterns = ['error', 'bug', 'implementation', 'algorithm', 'function', 'class', 'method']
        if any(pattern in query.lower() for pattern in technical_patterns):
            importance += 0.2

        # Boost for specific identifiers (camelCase, snake_case)
        if any(c.isupper() for c in query[1:]) or '_' in query:
            importance += 0.1

        # Boost for longer, more specific queries
        word_count = len(query.split())
        if word_count > 5:
            importance += 0.1

        # Check if query matches patterns commonly found in deduplicated content
        if self._matches_common_dedup_patterns(query):
            importance += 0.1  # Deduplicated content tends to be higher quality

        return min(importance, 1.0)

    def _matches_common_dedup_patterns(self, query: str) -> bool:
        """Check if query matches patterns commonly found in deduplicated content.

        Args:
            query: The search query

        Returns:
            True if query matches common dedup patterns
        """
        # Patterns that often get deduplicated (technical terms, code references)
        dedup_patterns = [
            'config', 'setting', 'preference', 'option',
            'api', 'endpoint', 'request', 'response',
            'test', 'spec', 'mock', 'fixture'
        ]
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in dedup_patterns)

    def _adjust_k_for_deduplication(self, k: int, dedup_stats: Dict[str, Any]) -> int:
        """Adjust search parameters based on deduplication effectiveness.

        Args:
            k: Original number of results requested
            dedup_stats: Deduplication statistics

        Returns:
            Adjusted k value
        """
        if not dedup_stats:
            return k

        # If deduplication has been effective (removed many duplicates),
        # we can request fewer results since quality should be higher
        duplicates_removed = dedup_stats.get('total_duplicates_removed', 0)
        total_processed = dedup_stats.get('total_documents_processed', 1)

        if total_processed > 0:
            dedup_ratio = duplicates_removed / total_processed
            if dedup_ratio > 0.3:  # >30% were duplicates
                # Collections are cleaner, we can be more selective
                return max(k, int(k * 0.8))

        return k
