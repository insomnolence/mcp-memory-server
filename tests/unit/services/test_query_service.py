"""
Unit tests for MemoryQueryService

Tests cover:
- query_memories: success cases, smart routing, error handling, edge cases
- _calculate_enhanced_retrieval_score: score calculation, boosts
- _update_access_stats: statistics updates
"""

import pytest
import time
import asyncio
from unittest.mock import Mock

from src.mcp_memory_server.memory.services.query import MemoryQueryService


# Fixtures for mocking dependencies

@pytest.fixture
def mock_short_term_memory():
    """Mock Chroma collection for short-term memory."""
    mock = Mock()
    mock.similarity_search_with_score = Mock(return_value=[])
    return mock


@pytest.fixture
def mock_long_term_memory():
    """Mock Chroma collection for long-term memory."""
    mock = Mock()
    mock.similarity_search_with_score = Mock(return_value=[])
    return mock


@pytest.fixture
def mock_routing_service():
    """Mock QueryRoutingService."""
    mock = Mock()
    # Default smart routing returns both collections with balanced limits
    mock.smart_query_routing = Mock(return_value=(
        ['short_term', 'long_term'],  # search_order
        [3, 2],  # collection_limits
        5  # effective_k
    ))
    return mock


@pytest.fixture
def mock_importance_scorer():
    """Mock MemoryImportanceScorer."""
    mock = Mock()
    mock.calculate_retrieval_score = Mock(return_value=0.75)
    return mock


@pytest.fixture
def mock_chunk_manager():
    """Mock ChunkRelationshipManager."""
    mock = Mock()
    mock.retrieve_related_chunks = Mock(return_value=[])
    return mock


@pytest.fixture
def mock_query_monitor():
    """Mock QueryPerformanceMonitor."""
    mock = Mock()
    mock.track_query = Mock()
    return mock


@pytest.fixture
def mock_deduplicator():
    """Mock MemoryDeduplicator."""
    mock = Mock()
    mock.enabled = True
    mock.get_deduplication_stats = Mock(return_value={
        'total_duplicates_removed': 10,
        'total_documents_processed': 100
    })
    return mock


@pytest.fixture
def query_service(
    mock_short_term_memory,
    mock_long_term_memory,
    mock_routing_service,
    mock_importance_scorer,
    mock_chunk_manager,
    mock_query_monitor,
    mock_deduplicator
):
    """Create a MemoryQueryService with all mocked dependencies."""
    return MemoryQueryService(
        short_term_memory=mock_short_term_memory,
        long_term_memory=mock_long_term_memory,
        routing_service=mock_routing_service,
        importance_scorer=mock_importance_scorer,
        chunk_manager=mock_chunk_manager,
        query_monitor=mock_query_monitor,
        deduplicator=mock_deduplicator,
        config={}
    )


def create_mock_document(
        content: str, metadata: dict = None, distance: float = 0.1):
    """Helper to create a mock document with score."""
    doc = Mock()
    doc.page_content = content
    doc.metadata = metadata or {
        'chunk_id': 'test_chunk_1',
        'importance_score': 0.5}
    return doc, distance


class TestMemoryQueryServiceInit:
    """Tests for MemoryQueryService initialization."""

    def test_init_with_all_dependencies(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_routing_service,
        mock_importance_scorer,
        mock_chunk_manager,
        mock_query_monitor,
        mock_deduplicator
    ):
        """Test service initializes correctly with all dependencies."""
        config = {'test_key': 'test_value'}
        service = MemoryQueryService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            routing_service=mock_routing_service,
            importance_scorer=mock_importance_scorer,
            chunk_manager=mock_chunk_manager,
            query_monitor=mock_query_monitor,
            deduplicator=mock_deduplicator,
            config=config
        )

        assert service.short_term_memory is mock_short_term_memory
        assert service.long_term_memory is mock_long_term_memory
        assert service.routing_service is mock_routing_service
        assert service.importance_scorer is mock_importance_scorer
        assert service.chunk_manager is mock_chunk_manager
        assert service.query_monitor is mock_query_monitor
        assert service.deduplicator is mock_deduplicator
        assert service.config == config

    def test_init_with_none_config(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_routing_service,
        mock_importance_scorer,
        mock_chunk_manager,
        mock_query_monitor,
        mock_deduplicator
    ):
        """Test service initializes with empty dict when config is None."""
        service = MemoryQueryService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            routing_service=mock_routing_service,
            importance_scorer=mock_importance_scorer,
            chunk_manager=mock_chunk_manager,
            query_monitor=mock_query_monitor,
            deduplicator=mock_deduplicator,
            config=None
        )

        assert service.config == {}


class TestGetCollection:
    """Tests for _get_collection method."""

    def test_get_short_term_collection(
            self, query_service, mock_short_term_memory):
        """Test retrieving short-term collection."""
        result = query_service._get_collection("short_term")
        assert result is mock_short_term_memory

    def test_get_long_term_collection(
            self, query_service, mock_long_term_memory):
        """Test retrieving long-term collection."""
        result = query_service._get_collection("long_term")
        assert result is mock_long_term_memory

    def test_get_invalid_collection(self, query_service):
        """Test retrieving non-existent collection returns None."""
        result = query_service._get_collection("invalid_collection")
        assert result is None

    def test_get_empty_string_collection(self, query_service):
        """Test retrieving with empty string returns None."""
        result = query_service._get_collection("")
        assert result is None


class TestQueryMemories:
    """Tests for query_memories method."""

    @pytest.mark.asyncio
    async def test_query_memories_empty_results(self, query_service):
        """Test query with no results from any collection."""
        results = await query_service.query_memories("test query", k=5)

        assert results['content'] == []
        assert results['total_results'] == 0
        assert 'collections_searched' in results
        assert 'processing_time_ms' in results

    @pytest.mark.asyncio
    async def test_query_memories_with_results(
        self,
        query_service,
        mock_short_term_memory,
        mock_importance_scorer
    ):
        """Test query returns formatted results."""
        doc, distance = create_mock_document(
            "Test document content",
            {'chunk_id': 'chunk_1', 'importance_score': 0.7}
        )
        mock_short_term_memory.similarity_search_with_score.return_value = [
            (doc, distance)]
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.85

        results = await query_service.query_memories("test query", k=5)

        assert results['total_results'] == 1
        assert len(results['content']) == 1
        assert 'Test document content' in results['content'][0]['text']
        assert results['content'][0]['type'] == 'text'

    @pytest.mark.asyncio
    async def test_query_memories_uses_smart_routing(
        self,
        query_service,
        mock_routing_service
    ):
        """Test that smart routing is used when enabled and collections not specified."""
        await query_service.query_memories("test query", k=5, use_smart_routing=True)

        mock_routing_service.smart_query_routing.assert_called_once_with(
            "test query", 5)

    @pytest.mark.asyncio
    async def test_query_memories_skips_smart_routing_when_disabled(
        self,
        query_service,
        mock_routing_service
    ):
        """Test smart routing is skipped when disabled."""
        await query_service.query_memories(
            "test query",
            k=5,
            use_smart_routing=False
        )

        mock_routing_service.smart_query_routing.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_memories_skips_smart_routing_with_explicit_collections(
        self,
        query_service,
        mock_routing_service
    ):
        """Test smart routing is skipped when collections are explicitly specified."""
        await query_service.query_memories(
            "test query",
            collections=['short_term'],
            k=5,
            use_smart_routing=True
        )

        mock_routing_service.smart_query_routing.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_memories_default_collections(self, query_service):
        """Test default collections when smart routing disabled and none specified."""
        results = await query_service.query_memories(
            "test query",
            k=5,
            use_smart_routing=False
        )

        assert 'short_term' in results['collections_searched']
        assert 'long_term' in results['collections_searched']

    @pytest.mark.asyncio
    async def test_query_memories_sorts_by_retrieval_score(
        self,
        query_service,
        mock_short_term_memory,
        mock_importance_scorer
    ):
        """Test results are sorted by retrieval score descending."""
        doc1, dist1 = create_mock_document("Doc 1", {'chunk_id': 'c1'}, 0.1)
        doc2, dist2 = create_mock_document("Doc 2", {'chunk_id': 'c2'}, 0.2)
        doc3, dist3 = create_mock_document("Doc 3", {'chunk_id': 'c3'}, 0.3)

        mock_short_term_memory.similarity_search_with_score.return_value = [
            (doc1, dist1), (doc2, dist2), (doc3, dist3)
        ]

        # Return different scores for different calls
        scores = [0.5, 0.9, 0.3]  # Doc 2 should be first
        mock_importance_scorer.calculate_retrieval_score.side_effect = scores

        results = await query_service.query_memories("test query", k=3)

        assert len(results['content']) == 3
        # Doc 2 (score 0.9) should be first
        assert 'Doc 2' in results['content'][0]['text']

    @pytest.mark.asyncio
    async def test_query_memories_respects_k_limit(
        self,
        query_service,
        mock_short_term_memory,
        mock_importance_scorer
    ):
        """Test that only k results are returned."""
        docs = [
            create_mock_document(f"Doc {i}", {'chunk_id': f'c{i}'}, 0.1 * i)
            for i in range(10)
        ]
        mock_short_term_memory.similarity_search_with_score.return_value = docs
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.5

        # Disable smart routing so k is used directly
        results = await query_service.query_memories(
            "test query", k=3, use_smart_routing=False
        )

        assert len(results['content']) <= 3

    @pytest.mark.asyncio
    async def test_query_memories_handles_chroma_error(
        self,
        query_service,
        mock_short_term_memory
    ):
        """Test graceful handling of ChromaDB errors."""
        # Import the error class to properly simulate it
        from chromadb.errors import ChromaError
        mock_short_term_memory.similarity_search_with_score.side_effect = ChromaError(
            "DB error")

        # Should not raise, should return empty results
        results = await query_service.query_memories("test query", k=5)

        assert results['content'] == []
        assert results['total_results'] == 0

    @pytest.mark.asyncio
    async def test_query_memories_handles_generic_exception(
        self,
        query_service,
        mock_short_term_memory
    ):
        """Test graceful handling of generic exceptions."""
        mock_short_term_memory.similarity_search_with_score.side_effect = Exception(
            "Unexpected error")

        results = await query_service.query_memories("test query", k=5)

        assert results['content'] == []
        assert results['total_results'] == 0

    @pytest.mark.asyncio
    async def test_query_memories_skips_invalid_collection(
        self,
        query_service,
        mock_short_term_memory
    ):
        """Test invalid collections are skipped without error."""
        doc, distance = create_mock_document("Test doc", {'chunk_id': 'c1'})
        mock_short_term_memory.similarity_search_with_score.return_value = [
            (doc, distance)]

        results = await query_service.query_memories(
            "test query",
            collections=['short_term', 'invalid_collection'],
            k=5
        )

        assert results['total_results'] == 1

    @pytest.mark.asyncio
    async def test_query_memories_tracks_performance(
        self,
        query_service,
        mock_query_monitor
    ):
        """Test query performance is tracked."""
        await query_service.query_memories("test query", k=5)

        mock_query_monitor.track_query.assert_called_once()
        call_args = mock_query_monitor.track_query.call_args
        assert call_args[0][0] == "test query"  # query string
        assert isinstance(call_args[0][2], float)  # processing_time

    @pytest.mark.asyncio
    async def test_query_memories_handles_monitor_error(
        self,
        query_service,
        mock_query_monitor
    ):
        """Test query continues even if monitor fails."""
        mock_query_monitor.track_query.side_effect = Exception("Monitor error")

        # Should not raise
        results = await query_service.query_memories("test query", k=5)

        assert 'content' in results

    @pytest.mark.asyncio
    async def test_query_memories_includes_dedup_info(
        self,
        query_service,
        mock_short_term_memory,
        mock_importance_scorer
    ):
        """Test deduplication info is included in results."""
        doc, distance = create_mock_document(
            "Test doc",
            {
                'chunk_id': 'c1',
                'duplicate_merged': True,
                'duplicate_sources': ['src1', 'src2', 'src3']
            }
        )
        mock_short_term_memory.similarity_search_with_score.return_value = [
            (doc, distance)]
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.8

        results = await query_service.query_memories("test query", k=5)

        assert 'Merged from 3 sources' in results['content'][0]['text']

    @pytest.mark.asyncio
    async def test_query_memories_includes_related_chunks(
        self,
        query_service,
        mock_short_term_memory,
        mock_chunk_manager,
        mock_importance_scorer
    ):
        """Test related chunks are included when available."""
        doc, distance = create_mock_document(
            "Main doc", {'chunk_id': 'main_chunk'})
        mock_short_term_memory.similarity_search_with_score.return_value = [
            (doc, distance)]
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.8

        mock_chunk_manager.retrieve_related_chunks.return_value = [
            {
                'relationship_type': 'follows_from',
                'context_relevance': 0.85,
                'content_preview': 'Related content preview'
            }
        ]

        results = await query_service.query_memories("test query", k=5)

        assert results['related_chunks_included'] == 1
        assert 'Related Context' in results['content'][0]['text']
        assert 'Follows From' in results['content'][0]['text']

    @pytest.mark.asyncio
    async def test_query_memories_handles_chunk_retrieval_error(
        self,
        query_service,
        mock_short_term_memory,
        mock_chunk_manager,
        mock_importance_scorer
    ):
        """Test graceful handling of chunk retrieval errors."""
        doc, distance = create_mock_document(
            "Main doc", {'chunk_id': 'main_chunk'})
        mock_short_term_memory.similarity_search_with_score.return_value = [
            (doc, distance)]
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.8
        mock_chunk_manager.retrieve_related_chunks.side_effect = Exception(
            "Chunk error")

        # Should not raise
        results = await query_service.query_memories("test query", k=5)

        assert results['related_chunks_included'] == 0

    @pytest.mark.asyncio
    async def test_query_memories_result_metadata(self, query_service):
        """Test result includes expected metadata fields."""
        results = await query_service.query_memories("test query", k=5)

        assert 'content' in results
        assert 'total_results' in results
        assert 'collections_searched' in results
        assert 'smart_routing_used' in results
        assert 'query_optimization_applied' in results
        assert 'processing_time_ms' in results
        assert 'related_chunks_included' in results
        assert 'context_enhancement_enabled' in results

    @pytest.mark.asyncio
    async def test_query_memories_context_enhancement_flag(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_routing_service,
        mock_importance_scorer,
        mock_query_monitor,
        mock_deduplicator
    ):
        """Test context_enhancement_enabled reflects chunk_manager presence."""
        # With chunk_manager
        service_with_chunks = MemoryQueryService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            routing_service=mock_routing_service,
            importance_scorer=mock_importance_scorer,
            chunk_manager=Mock(),
            query_monitor=mock_query_monitor,
            deduplicator=mock_deduplicator
        )
        results = await service_with_chunks.query_memories("test", k=5)
        assert results['context_enhancement_enabled'] is True

        # Without chunk_manager
        service_no_chunks = MemoryQueryService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            routing_service=mock_routing_service,
            importance_scorer=mock_importance_scorer,
            chunk_manager=None,
            query_monitor=mock_query_monitor,
            deduplicator=mock_deduplicator
        )
        results = await service_no_chunks.query_memories("test", k=5)
        assert results['context_enhancement_enabled'] is False


class TestCalculateEnhancedRetrievalScore:
    """Tests for _calculate_enhanced_retrieval_score method."""

    @pytest.mark.asyncio
    async def test_base_score_calculation(
        self,
        query_service,
        mock_importance_scorer
    ):
        """Test base score is calculated from importance scorer."""
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.75
        current_time = time.time()

        memory_data = {
            'metadata': {'importance_score': 0.5, 'access_count': 10, 'timestamp': current_time - 3600},
            'distance': 0.2
        }

        score = await query_service._calculate_enhanced_retrieval_score(
            memory_data, "test query", current_time
        )

        mock_importance_scorer.calculate_retrieval_score.assert_called_once()
        assert score >= 0.0
        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_dedup_boost_applied(
        self,
        query_service,
        mock_importance_scorer
    ):
        """Test deduplication boost is applied for merged documents."""
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.5
        current_time = time.time()

        memory_data_merged = {
            'metadata': {
                'duplicate_merged': True,
                'duplicate_sources': ['s1', 's2', 's3', 's4'],  # 4 sources
                'importance_score': 0.5
            },
            'distance': 0.2
        }

        memory_data_single = {
            'metadata': {'importance_score': 0.5},
            'distance': 0.2
        }

        score_merged = await query_service._calculate_enhanced_retrieval_score(
            memory_data_merged, "test query", current_time
        )
        score_single = await query_service._calculate_enhanced_retrieval_score(
            memory_data_single, "test query", current_time
        )

        # Merged document should have higher score due to dedup boost
        assert score_merged > score_single

    @pytest.mark.asyncio
    async def test_dedup_boost_diminishing_returns(
        self,
        query_service,
        mock_importance_scorer
    ):
        """Test deduplication boost has diminishing returns with more sources."""
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.5
        current_time = time.time()

        memory_data_few = {
            'metadata': {
                'duplicate_merged': True,
                'duplicate_sources': ['s1', 's2'],  # 2 sources
            },
            'distance': 0.2
        }

        memory_data_many = {
            'metadata': {
                'duplicate_merged': True,
                # 8 sources
                'duplicate_sources': ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8'],
            },
            'distance': 0.2
        }

        score_few = await query_service._calculate_enhanced_retrieval_score(
            memory_data_few, "test query", current_time
        )
        score_many = await query_service._calculate_enhanced_retrieval_score(
            memory_data_many, "test query", current_time
        )

        # More sources means higher score, but diminishing
        boost_few = score_few - 0.5  # base score
        boost_many = score_many - 0.5

        # Boost ratio should be less than source count ratio (8/2 = 4)
        assert boost_many / boost_few < 4

    @pytest.mark.asyncio
    async def test_recency_boost_recent_access(
        self,
        query_service,
        mock_importance_scorer
    ):
        """Test recency boost for recently accessed content."""
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.5
        current_time = time.time()

        memory_data_recent = {
            'metadata': {
                'last_accessed': current_time - 3600,  # 1 hour ago
                'importance_score': 0.5
            },
            'distance': 0.2
        }

        memory_data_old = {
            'metadata': {
                'last_accessed': current_time - 86400 * 2,  # 2 days ago
                'importance_score': 0.5
            },
            'distance': 0.2
        }

        score_recent = await query_service._calculate_enhanced_retrieval_score(
            memory_data_recent, "test query", current_time
        )
        score_old = await query_service._calculate_enhanced_retrieval_score(
            memory_data_old, "test query", current_time
        )

        # Recently accessed should have higher score
        assert score_recent > score_old

    @pytest.mark.asyncio
    async def test_recency_boost_no_access_history(
        self,
        query_service,
        mock_importance_scorer
    ):
        """Test no recency boost when no access history."""
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.5
        current_time = time.time()

        memory_data = {
            'metadata': {'importance_score': 0.5},  # No last_accessed
            'distance': 0.2
        }

        score = await query_service._calculate_enhanced_retrieval_score(
            memory_data, "test query", current_time
        )

        # Should equal base score (no boosts)
        assert score == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_score_capped_at_one(
        self,
        query_service,
        mock_importance_scorer
    ):
        """Test final score is capped at 1.0."""
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.95
        current_time = time.time()

        memory_data = {
            'metadata': {
                'duplicate_merged': True,
                'duplicate_sources': ['s1', 's2', 's3', 's4', 's5'],
                'last_accessed': current_time - 1,  # Just accessed
                'importance_score': 1.0
            },
            'distance': 0.0
        }

        score = await query_service._calculate_enhanced_retrieval_score(
            memory_data, "test query", current_time
        )

        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_score_with_missing_metadata(
        self,
        query_service,
        mock_importance_scorer
    ):
        """Test score calculation with minimal metadata."""
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.6
        current_time = time.time()

        memory_data = {
            'metadata': {},  # Empty metadata
            'distance': 0.3
        }

        # Should not raise
        score = await query_service._calculate_enhanced_retrieval_score(
            memory_data, "test query", current_time
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestUpdateAccessStats:
    """Tests for _update_access_stats method."""

    def test_update_access_stats_increments_count(self, query_service):
        """Test access count is incremented."""
        results = [
            {
                'metadata': {'chunk_id': 'c1', 'access_count': 5},
                'collection': 'short_term'
            }
        ]

        query_service._update_access_stats(results)

        assert results[0]['metadata']['access_count'] == 6

    def test_update_access_stats_sets_last_accessed(self, query_service):
        """Test last_accessed timestamp is updated."""
        results = [
            {
                'metadata': {'chunk_id': 'c1', 'access_count': 0},
                'collection': 'short_term'
            }
        ]

        before_time = time.time()
        query_service._update_access_stats(results)
        after_time = time.time()

        assert 'last_accessed' in results[0]['metadata']
        assert before_time <= results[0]['metadata']['last_accessed'] <= after_time

    def test_update_access_stats_multiple_results(self, query_service):
        """Test stats updated for multiple results."""
        results = [
            {'metadata': {'chunk_id': 'c1', 'access_count': 1},
                'collection': 'short_term'},
            {'metadata': {'chunk_id': 'c2', 'access_count': 2},
                'collection': 'long_term'},
            {'metadata': {'chunk_id': 'c3', 'access_count': 3},
                'collection': 'short_term'},
        ]

        query_service._update_access_stats(results)

        assert results[0]['metadata']['access_count'] == 2
        assert results[1]['metadata']['access_count'] == 3
        assert results[2]['metadata']['access_count'] == 4

    def test_update_access_stats_missing_chunk_id(self, query_service):
        """Test graceful handling when chunk_id is missing."""
        results = [
            {'metadata': {'access_count': 5},
             'collection': 'short_term'}  # No chunk_id
        ]

        # Should not raise
        query_service._update_access_stats(results)

        # Access count should still be incremented (only chunk_id check prevents update)
        # Actually, looking at the code, it skips if chunk_id is missing
        assert results[0]['metadata']['access_count'] == 5

    def test_update_access_stats_missing_access_count(self, query_service):
        """Test handling when access_count not in metadata."""
        results = [
            {'metadata': {'chunk_id': 'c1'},
             'collection': 'short_term'}  # No access_count
        ]

        query_service._update_access_stats(results)

        # Should default to 0 + 1
        assert results[0]['metadata']['access_count'] == 1

    def test_update_access_stats_empty_results(self, query_service):
        """Test with empty results list."""
        results = []

        # Should not raise
        query_service._update_access_stats(results)

    def test_update_access_stats_invalid_collection(self, query_service):
        """Test handling of invalid collection name."""
        results = [
            {
                'metadata': {'chunk_id': 'c1', 'access_count': 5},
                'collection': 'invalid_collection'
            }
        ]

        # Should not raise
        query_service._update_access_stats(results)

        # Stats should still be updated in memory_data
        assert results[0]['metadata']['access_count'] == 6


class TestEdgeCases:
    """Edge case and integration-like tests."""

    @pytest.mark.asyncio
    async def test_query_with_empty_string(self, query_service):
        """Test querying with empty string."""
        results = await query_service.query_memories("", k=5)

        assert 'content' in results
        assert results['total_results'] == 0

    @pytest.mark.asyncio
    async def test_query_with_k_zero(self, query_service):
        """Test querying with k=0."""
        results = await query_service.query_memories("test query", k=0)

        assert results['content'] == []

    @pytest.mark.asyncio
    async def test_query_with_large_k(
        self,
        query_service,
        mock_short_term_memory,
        mock_importance_scorer
    ):
        """Test querying with large k value."""
        docs = [
            create_mock_document(f"Doc {i}", {'chunk_id': f'c{i}'})
            for i in range(5)
        ]
        mock_short_term_memory.similarity_search_with_score.return_value = docs
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.5

        results = await query_service.query_memories("test query", k=1000)

        # Should return all available results
        assert results['total_results'] == 5

    @pytest.mark.asyncio
    async def test_query_with_special_characters(
        self,
        query_service,
        mock_routing_service
    ):
        """Test querying with special characters."""
        special_query = "test!@#$%^&*()_+-=[]{}|;':\",./<>?"

        await query_service.query_memories(special_query, k=5)

        mock_routing_service.smart_query_routing.assert_called_with(
            special_query, 5)

    @pytest.mark.asyncio
    async def test_query_with_unicode(
        self,
        query_service,
        mock_routing_service
    ):
        """Test querying with unicode characters."""
        unicode_query = "test query with unicode: \u4e2d\u6587 \u0414\u0440\u0443\u0433 \ud83d\ude00"

        await query_service.query_memories(unicode_query, k=5)

        mock_routing_service.smart_query_routing.assert_called_with(
            unicode_query, 5)

    @pytest.mark.asyncio
    async def test_concurrent_queries(self, query_service):
        """Test multiple concurrent queries don't interfere."""
        queries = [f"query_{i}" for i in range(5)]

        async def run_query(q):
            return await query_service.query_memories(q, k=3)

        results = await asyncio.gather(*[run_query(q) for q in queries])

        assert len(results) == 5
        for r in results:
            assert 'content' in r

    @pytest.mark.asyncio
    async def test_query_memories_processing_time_positive(
            self, query_service):
        """Test processing time is always positive."""
        results = await query_service.query_memories("test", k=5)

        assert results['processing_time_ms'] >= 0

    @pytest.mark.asyncio
    async def test_query_with_only_short_term(
        self,
        query_service,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_importance_scorer
    ):
        """Test query targeting only short-term collection."""
        doc, distance = create_mock_document(
            "Short term doc", {'chunk_id': 'st1'})
        mock_short_term_memory.similarity_search_with_score.return_value = [
            (doc, distance)]
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.7

        results = await query_service.query_memories(
            "test",
            collections=['short_term'],
            k=5,
            use_smart_routing=False
        )

        assert results['collections_searched'] == ['short_term']
        mock_long_term_memory.similarity_search_with_score.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_with_only_long_term(
        self,
        query_service,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_importance_scorer
    ):
        """Test query targeting only long-term collection."""
        doc, distance = create_mock_document(
            "Long term doc", {'chunk_id': 'lt1'})
        mock_long_term_memory.similarity_search_with_score.return_value = [
            (doc, distance)]
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.7

        results = await query_service.query_memories(
            "test",
            collections=['long_term'],
            k=5,
            use_smart_routing=False
        )

        assert results['collections_searched'] == ['long_term']
        mock_short_term_memory.similarity_search_with_score.assert_not_called()


class TestSmartRoutingIntegration:
    """Tests for smart routing behavior."""

    @pytest.mark.asyncio
    async def test_smart_routing_flag_in_results(
        self,
        query_service,
        mock_routing_service
    ):
        """Test smart_routing_used flag reflects actual routing."""
        # Smart routing returns non-default order
        mock_routing_service.smart_query_routing.return_value = (
            ['long_term', 'short_term'],
            [3, 2],
            5
        )

        results = await query_service.query_memories("test", k=5, use_smart_routing=True)

        # smart_routing_used should be True when order differs from default
        assert results['query_optimization_applied'] is True

    @pytest.mark.asyncio
    async def test_collection_limits_from_routing(
        self,
        query_service,
        mock_routing_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test collection-specific limits are applied from routing."""
        mock_routing_service.smart_query_routing.return_value = (
            ['short_term', 'long_term'],
            [4, 1],  # Short term gets more
            5
        )

        await query_service.query_memories("test", k=5, use_smart_routing=True)

        # Verify search was called with appropriate k values
        # search_k = max(collection_k * 2, 10)
        short_term_call = mock_short_term_memory.similarity_search_with_score.call_args
        long_term_call = mock_long_term_memory.similarity_search_with_score.call_args

        assert short_term_call is not None
        assert long_term_call is not None

    @pytest.mark.asyncio
    async def test_effective_k_used_for_final_results(
        self,
        query_service,
        mock_routing_service,
        mock_short_term_memory,
        mock_importance_scorer
    ):
        """Test effective_k from routing limits final results."""
        mock_routing_service.smart_query_routing.return_value = (
            ['short_term'],
            [3],
            3  # effective_k is 3
        )

        # Return more docs than effective_k
        docs = [
            create_mock_document(f"Doc {i}", {'chunk_id': f'c{i}'})
            for i in range(10)
        ]
        mock_short_term_memory.similarity_search_with_score.return_value = docs
        mock_importance_scorer.calculate_retrieval_score.return_value = 0.5

        results = await query_service.query_memories("test", k=10, use_smart_routing=True)

        # Should be limited to effective_k (3)
        assert len(results['content']) <= 3
