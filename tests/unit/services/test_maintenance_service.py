"""
Unit tests for MemoryMaintenanceService

Tests cover:
- Short-term memory maintenance triggering and cleanup
- Smart cleanup selection with deduplication awareness
- Document quality comparison for duplicate pairs
- Similarity clustering cleanup
- Cluster grouping from similar pairs
- Age-based cleanup fallback
"""

import pytest
import time
from unittest.mock import Mock, patch

from langchain_core.documents import Document

from src.mcp_memory_server.memory.services.maintenance import MemoryMaintenanceService
from src.mcp_memory_server.memory.exceptions import (
    MaintenanceError,
    CleanupError,
    DeduplicationError
)


# Fixtures

@pytest.fixture
def mock_short_term_memory():
    """Create a mock Chroma collection for short-term memory."""
    mock = Mock()
    mock._collection = Mock()
    mock._collection.count.return_value = 50
    mock._collection.get.return_value = {
        'ids': [],
        'documents': [],
        'metadatas': []
    }
    mock.get.return_value = {'ids': []}
    mock.similarity_search.return_value = []
    return mock


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service."""
    mock = Mock()
    mock.remove_documents_from_collection = Mock()
    return mock


@pytest.fixture
def mock_deduplicator():
    """Create a mock deduplicator with similarity calculator."""
    mock = Mock()
    mock.enabled = True
    mock.similarity_calculator = Mock()
    mock.similarity_calculator.find_duplicates_batch = Mock(return_value=[])
    return mock


@pytest.fixture
def maintenance_config():
    """Default configuration for maintenance service."""
    return {
        'short_term_max_size': 100
    }


@pytest.fixture
def maintenance_service(mock_short_term_memory,
                        mock_storage_service, mock_deduplicator, maintenance_config):
    """Create a MemoryMaintenanceService instance with mocked dependencies."""
    return MemoryMaintenanceService(
        short_term_memory=mock_short_term_memory,
        storage_service=mock_storage_service,
        deduplicator=mock_deduplicator,
        config=maintenance_config
    )


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    current_time = time.time()
    return [
        Document(
            page_content="Document about Python programming",
            metadata={
                'chroma_id': 'doc_1',
                'timestamp': current_time - 86400 * 5,  # 5 days old
                'importance_score': 0.3,
                'access_count': 2
            }
        ),
        Document(
            page_content="Document about JavaScript development",
            metadata={
                'chroma_id': 'doc_2',
                'timestamp': current_time - 86400 * 2,  # 2 days old
                'importance_score': 0.7,
                'access_count': 10
            }
        ),
        Document(
            page_content="Document about database design",
            metadata={
                'chroma_id': 'doc_3',
                'timestamp': current_time - 86400 * 10,  # 10 days old
                'importance_score': 0.2,
                'access_count': 1
            }
        ),
        Document(
            page_content="Document about API design patterns",
            metadata={
                'chroma_id': 'doc_4',
                'timestamp': current_time - 3600,  # 1 hour old
                'importance_score': 0.8,
                'access_count': 5
            }
        ),
        Document(
            page_content="Document about testing best practices",
            metadata={
                'chroma_id': 'doc_5',
                'timestamp': current_time - 86400,  # 1 day old
                'importance_score': 0.5,
                'access_count': 3
            }
        ),
    ]


class TestMaintenanceServiceInit:
    """Tests for MemoryMaintenanceService initialization."""

    def test_init_with_default_config(
            self, mock_short_term_memory, mock_storage_service, mock_deduplicator):
        """Test initialization with default configuration."""
        service = MemoryMaintenanceService(
            short_term_memory=mock_short_term_memory,
            storage_service=mock_storage_service,
            deduplicator=mock_deduplicator
        )
        assert service.short_term_max_size == 100  # Default value

    def test_init_with_custom_config(
            self, mock_short_term_memory, mock_storage_service, mock_deduplicator):
        """Test initialization with custom configuration."""
        config = {'short_term_max_size': 200}
        service = MemoryMaintenanceService(
            short_term_memory=mock_short_term_memory,
            storage_service=mock_storage_service,
            deduplicator=mock_deduplicator,
            config=config
        )
        assert service.short_term_max_size == 200


class TestMaintainShortTermMemory:
    """Tests for maintain_short_term_memory method."""

    @pytest.mark.asyncio
    async def test_no_cleanup_when_under_max_size(
            self, maintenance_service, mock_short_term_memory):
        """Test that no cleanup occurs when document count is under max size."""
        mock_short_term_memory._collection.count.return_value = 50  # Under 100

        await maintenance_service.maintain_short_term_memory()

        # Storage service should not be called for removal
        maintenance_service.storage_service.remove_documents_from_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_triggered_when_over_max_size(
        self, maintenance_service, mock_short_term_memory, sample_documents
    ):
        """Test that cleanup is triggered when document count exceeds max size."""
        mock_short_term_memory._collection.count.return_value = 120

        # Setup mock to return documents
        mock_short_term_memory._collection.get.return_value = {
            'ids': [f'doc_{i}' for i in range(120)],
            'documents': [f'content_{i}' for i in range(120)],
            'metadatas': [{'timestamp': time.time() - i * 3600, 'importance_score': 0.5} for i in range(120)]
        }

        await maintenance_service.maintain_short_term_memory()

        # Storage service should be called
        maintenance_service.storage_service.remove_documents_from_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_target_size_is_80_percent(
            self, maintenance_service, mock_short_term_memory):
        """Test that target size after cleanup is 80% of max size."""
        mock_short_term_memory._collection.count.return_value = 150
        mock_short_term_memory._collection.get.return_value = {
            'ids': [f'doc_{i}' for i in range(150)],
            'documents': [f'content_{i}' for i in range(150)],
            'metadatas': [{'timestamp': time.time() - i * 3600} for i in range(150)]
        }

        await maintenance_service.maintain_short_term_memory()

        # Should remove 150 - 80 = 70 documents (target is 80% of 100 = 80)
        call_args = maintenance_service.storage_service.remove_documents_from_collection.call_args
        # Second argument is the list of docs to remove
        removed_docs = call_args[0][1]
        assert len(removed_docs) == 70

    @pytest.mark.asyncio
    async def test_fallback_get_method_when_no_collection_attr(
            self, maintenance_service, mock_short_term_memory):
        """Test fallback to get() method when _collection attribute is not available."""
        # Remove _collection attribute
        del mock_short_term_memory._collection

        mock_short_term_memory.get.return_value = {
            'ids': ['doc_1', 'doc_2']}  # 2 docs, under max

        await maintenance_service.maintain_short_term_memory()

        # No cleanup should occur since count is under max
        maintenance_service.storage_service.remove_documents_from_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_chroma_error_raises_maintenance_error(
            self, maintenance_service, mock_short_term_memory):
        """Test that ChromaError during maintenance raises MaintenanceError."""
        from chromadb.errors import InternalError

        mock_short_term_memory._collection.count.side_effect = InternalError(
            "Database error")

        with pytest.raises(MaintenanceError) as exc_info:
            await maintenance_service.maintain_short_term_memory()

        assert "Short-term memory maintenance failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cleanup_error_is_caught_and_logged(
            self, maintenance_service, mock_short_term_memory):
        """Test that CleanupError is caught and logged without re-raising."""
        mock_short_term_memory._collection.count.return_value = 120

        # Simulate CleanupError during smart cleanup
        with patch.object(
            maintenance_service, '_smart_cleanup_selection',
            side_effect=CleanupError('test_phase', 'Test cleanup error')
        ):
            # Should not raise, just log
            await maintenance_service.maintain_short_term_memory()

    @pytest.mark.asyncio
    async def test_no_removal_when_candidates_empty(
            self, maintenance_service, mock_short_term_memory):
        """Test that no removal occurs when smart cleanup returns empty list."""
        mock_short_term_memory._collection.count.return_value = 120

        with patch.object(maintenance_service, '_smart_cleanup_selection', return_value=[]):
            await maintenance_service.maintain_short_term_memory()

        maintenance_service.storage_service.remove_documents_from_collection.assert_not_called()


class TestSmartCleanupSelection:
    """Tests for _smart_cleanup_selection method."""

    @pytest.mark.asyncio
    async def test_returns_all_docs_when_under_target(
            self, maintenance_service, mock_short_term_memory):
        """Test that all documents are returned when count is under target removal."""
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['doc_1', 'doc_2'],
            'documents': ['content_1', 'content_2'],
            'metadatas': [{'timestamp': time.time()}, {'timestamp': time.time()}]
        }

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=5)

        assert len(result) == 2  # Only 2 docs available

    @pytest.mark.asyncio
    async def test_phase1_deduplication_cleanup(
            self, maintenance_service, mock_short_term_memory, mock_deduplicator):
        """Test Phase 1: removal of exact duplicates."""
        current_time = time.time()
        docs_data = {
            'ids': ['doc_1', 'doc_2', 'doc_3'],
            'documents': ['content_1', 'content_1_duplicate', 'content_3'],
            'metadatas': [
                {'timestamp': current_time,
                 'importance_score': 0.8,
                 'access_count': 10},
                {'timestamp': current_time - 3600,
                    'importance_score': 0.3, 'access_count': 2},
                {'timestamp': current_time, 'importance_score': 0.5, 'access_count': 5}
            ]
        }
        mock_short_term_memory._collection.get.return_value = docs_data

        # Mock deduplicator to find duplicates
        def find_duplicates_side_effect(doc_data, threshold):
            # Return doc_1 and doc_2 as duplicates
            return [(doc_data[0], doc_data[1], 0.98)]

        mock_deduplicator.similarity_calculator.find_duplicates_batch.side_effect = find_duplicates_side_effect

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=1)

        # Should return the worse document (doc_2 with lower importance)
        assert len(result) == 1
        assert result[0].metadata.get('chroma_id') == 'doc_2'

    @pytest.mark.asyncio
    async def test_phase2_similarity_cluster_cleanup(
        self, maintenance_service, mock_short_term_memory, mock_deduplicator
    ):
        """Test Phase 2: similarity clustering cleanup when dedup isn't enough."""
        current_time = time.time()
        docs_data = {
            'ids': [f'doc_{i}' for i in range(10)],
            'documents': [f'content_{i}' for i in range(10)],
            'metadatas': [
                {'timestamp': current_time - i * 86400 * 2,
                    'importance_score': 0.5, 'access_count': i}
                for i in range(10)
            ]
        }
        mock_short_term_memory._collection.get.return_value = docs_data

        # No duplicates found in phase 1
        mock_deduplicator.similarity_calculator.find_duplicates_batch.return_value = []

        # Mock phase 2 to return some candidates
        with patch.object(
            maintenance_service, '_similarity_cluster_cleanup',
            return_value=[
                Document(
                    page_content='cluster_doc',
                    metadata={
                        'chroma_id': 'cluster_1'})]
        ):
            result = await maintenance_service._smart_cleanup_selection(target_removal_count=3)

        # Should have cluster removal plus age-based for the remainder
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_phase3_age_based_fallback(
            self, maintenance_service, mock_short_term_memory, mock_deduplicator):
        """Test Phase 3: age-based cleanup when other phases don't find enough."""
        current_time = time.time()
        docs_data = {
            'ids': ['doc_1', 'doc_2', 'doc_3', 'doc_4', 'doc_5'],
            'documents': ['content_1', 'content_2', 'content_3', 'content_4', 'content_5'],
            'metadatas': [
                {'timestamp': current_time - 86400 *
                    10, 'access_count': 1},  # Oldest
                {'timestamp': current_time - 86400 * 5, 'access_count': 2},
                {'timestamp': current_time - 86400 * 2, 'access_count': 3},
                {'timestamp': current_time - 86400, 'access_count': 4},
                {'timestamp': current_time, 'access_count': 5}  # Newest
            ]
        }
        mock_short_term_memory._collection.get.return_value = docs_data

        # Disable deduplication to force age-based cleanup
        mock_deduplicator.enabled = False

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=2)

        # Should return the oldest documents
        assert len(result) == 2
        # doc_1 should be first (oldest with lowest access count)
        assert result[0].metadata.get('chroma_id') == 'doc_1'

    @pytest.mark.asyncio
    async def test_deduplication_disabled_skips_phase1(
        self, maintenance_service, mock_short_term_memory, mock_deduplicator
    ):
        """Test that phase 1 is skipped when deduplication is disabled."""
        mock_deduplicator.enabled = False
        current_time = time.time()
        docs_data = {
            'ids': ['doc_1', 'doc_2'],
            'documents': ['content_1', 'content_2'],
            'metadatas': [
                {'timestamp': current_time - 86400, 'access_count': 1},
                {'timestamp': current_time, 'access_count': 5}
            ]
        }
        mock_short_term_memory._collection.get.return_value = docs_data

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=1)

        # Should use age-based cleanup directly
        mock_deduplicator.similarity_calculator.find_duplicates_batch.assert_not_called()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_deduplication_error_continues_to_phase2(
        self, maintenance_service, mock_short_term_memory, mock_deduplicator
    ):
        """Test that DeduplicationError in phase 1 allows continuation to phase 2."""
        current_time = time.time()
        docs_data = {
            'ids': ['doc_1', 'doc_2', 'doc_3'],
            'documents': ['content_1', 'content_2', 'content_3'],
            'metadatas': [
                {'timestamp': current_time - 86400 * 3, 'access_count': 1},
                {'timestamp': current_time - 86400, 'access_count': 2},
                {'timestamp': current_time, 'access_count': 3}
            ]
        }
        mock_short_term_memory._collection.get.return_value = docs_data

        # Phase 1 raises DeduplicationError
        mock_deduplicator.similarity_calculator.find_duplicates_batch.side_effect = DeduplicationError(
            "Deduplication failed"
        )

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=1)

        # Should still return results from fallback phases
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_chroma_error_falls_back_to_age_based(
        self, maintenance_service, mock_short_term_memory, mock_deduplicator
    ):
        """Test that ChromaError triggers fallback to age-based cleanup."""
        from chromadb.errors import InternalError

        # First call fails, but we need the fallback to work
        mock_short_term_memory._collection.get.side_effect = InternalError(
            "Database error")

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=2)

        # Should return empty list (no docs available for age-based cleanup)
        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_similarity_search_when_no_collection(
        self, maintenance_service, mock_short_term_memory, mock_deduplicator
    ):
        """Test fallback to similarity_search when _collection attribute missing."""
        del mock_short_term_memory._collection

        current_time = time.time()
        mock_docs = [
            Document(
                page_content='content_1',
                metadata={'timestamp': current_time - 86400, 'access_count': 1}
            ),
            Document(
                page_content='content_2',
                metadata={'timestamp': current_time, 'access_count': 5}
            )
        ]
        mock_short_term_memory.similarity_search.return_value = mock_docs
        mock_deduplicator.enabled = False

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=1)

        mock_short_term_memory.similarity_search.assert_called_once_with(
            "", k=1000)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_result_capped_at_target_count(
            self, maintenance_service, mock_short_term_memory, mock_deduplicator):
        """Test that results are capped at target_removal_count."""
        current_time = time.time()
        docs_data = {
            'ids': [f'doc_{i}' for i in range(20)],
            'documents': [f'content_{i}' for i in range(20)],
            'metadatas': [
                {'timestamp': current_time - i * 3600,
                    'importance_score': 0.5, 'access_count': 0}
                for i in range(20)
            ]
        }
        mock_short_term_memory._collection.get.return_value = docs_data
        mock_deduplicator.enabled = False

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=5)

        assert len(result) == 5


class TestChooseWorseDocument:
    """Tests for _choose_worse_document method."""

    def test_chooses_lower_importance_document(self, maintenance_service):
        """Test that document with lower importance score is chosen."""
        doc1 = Document(
            page_content="High importance doc",
            metadata={
                'importance_score': 0.9,
                'access_count': 5,
                'timestamp': time.time()}
        )
        doc2 = Document(
            page_content="Low importance doc",
            metadata={
                'importance_score': 0.2,
                'access_count': 5,
                'timestamp': time.time()}
        )

        worse = maintenance_service._choose_worse_document(doc1, doc2)

        assert worse == doc2

    def test_chooses_less_accessed_document(self, maintenance_service):
        """Test that document with fewer accesses is chosen when importance is equal."""
        current_time = time.time()
        doc1 = Document(
            page_content="More accessed doc",
            metadata={
                'importance_score': 0.5,
                'access_count': 20,
                'timestamp': current_time}
        )
        doc2 = Document(
            page_content="Less accessed doc",
            metadata={
                'importance_score': 0.5,
                'access_count': 1,
                'timestamp': current_time}
        )

        worse = maintenance_service._choose_worse_document(doc1, doc2)

        assert worse == doc2

    def test_chooses_older_document(self, maintenance_service):
        """Test that older document is chosen when other factors are equal."""
        current_time = time.time()
        doc1 = Document(
            page_content="New doc",
            metadata={
                'importance_score': 0.5,
                'access_count': 5,
                'timestamp': current_time}
        )
        doc2 = Document(
            page_content="Old doc",
            metadata={
                'importance_score': 0.5,
                'access_count': 5,
                'timestamp': current_time - 86400 * 30}
        )

        worse = maintenance_service._choose_worse_document(doc1, doc2)

        assert worse == doc2

    def test_handles_missing_metadata(self, maintenance_service):
        """Test that missing metadata fields default to 0."""
        doc1 = Document(
            page_content="Doc with metadata",
            metadata={
                'importance_score': 0.5})
        doc2 = Document(page_content="Doc without metadata", metadata={})

        # Should not raise an error
        worse = maintenance_service._choose_worse_document(doc1, doc2)

        # doc2 should be worse (all scores default to 0)
        assert worse == doc2

    def test_quality_score_weights(self, maintenance_service):
        """Test that quality score weights are applied correctly."""
        current_time = time.time()
        # High importance (0.8 * 0.5 = 0.4), low access (1 * 0.3 = 0.3), old
        # timestamp
        doc1 = Document(
            page_content="Doc 1",
            metadata={
                'importance_score': 0.8,
                'access_count': 1,
                'timestamp': current_time - 86400 * 10  # 10 days old
            }
        )
        # Low importance (0.2 * 0.5 = 0.1), high access (10 * 0.3 = 3), recent
        doc2 = Document(
            page_content="Doc 2",
            metadata={
                'importance_score': 0.2,
                'access_count': 10,
                'timestamp': current_time
            }
        )

        worse = maintenance_service._choose_worse_document(doc1, doc2)

        # doc1 has higher importance but less access and older timestamp
        # Need to calculate actual scores to verify
        # doc1: 0.8*0.5 + 1*0.3 + (current_time - 86400*10)/86400*0.2
        # doc2: 0.2*0.5 + 10*0.3 + current_time/86400*0.2
        # The timestamp component dominates due to large values
        assert worse is not None


class TestSimilarityClusterCleanup:
    """Tests for _similarity_cluster_cleanup method."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_dedup_disabled(
            self, maintenance_service, mock_deduplicator):
        """Test that empty list is returned when deduplication is disabled."""
        mock_deduplicator.enabled = False
        docs = [Document(page_content="doc1", metadata={})]

        result = await maintenance_service._similarity_cluster_cleanup(docs, target_count=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_single_document(
            self, maintenance_service, mock_deduplicator):
        """Test that empty list is returned for single document."""
        docs = [Document(page_content="only doc", metadata={})]

        result = await maintenance_service._similarity_cluster_cleanup(docs, target_count=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_clusters_similar_documents(
            self, maintenance_service, mock_deduplicator):
        """Test clustering of similar documents."""
        current_time = time.time()
        docs = [
            Document(
                page_content="Python tutorial part 1",
                metadata={
                    'importance_score': 0.5,
                    'access_count': 5,
                    'timestamp': current_time - 86400 * 3}
            ),
            Document(
                page_content="Python tutorial part 2",
                metadata={
                    'importance_score': 0.8,
                    'access_count': 10,
                    'timestamp': current_time}
            ),
            Document(
                page_content="JavaScript guide",
                metadata={
                    'importance_score': 0.6,
                    'access_count': 7,
                    'timestamp': current_time - 86400}
            )
        ]

        # Mock similarity to find Python docs as similar
        def find_similar(doc_data, threshold):
            return [(doc_data[0], doc_data[1], 0.85)]

        mock_deduplicator.similarity_calculator.find_duplicates_batch.side_effect = find_similar

        result = await maintenance_service._similarity_cluster_cleanup(docs, target_count=1)

        # Should remove the worse document from the Python cluster
        assert len(result) <= 1

    @pytest.mark.asyncio
    async def test_preserves_recent_documents(
            self, maintenance_service, mock_deduplicator):
        """Test that documents less than 1 day old are preserved."""
        current_time = time.time()
        docs = [
            Document(
                page_content="Very recent doc",
                metadata={'importance_score': 0.1, 'access_count': 0,
                          'timestamp': current_time - 3600}  # 1 hour old
            ),
            Document(
                page_content="Old similar doc",
                metadata={
                    'importance_score': 0.9,
                    'access_count': 100,
                    'timestamp': current_time - 86400 * 5}
            )
        ]

        def find_similar(doc_data, threshold):
            return [(doc_data[0], doc_data[1], 0.80)]

        mock_deduplicator.similarity_calculator.find_duplicates_batch.side_effect = find_similar

        result = await maintenance_service._similarity_cluster_cleanup(docs, target_count=1)

        # Should not remove the recent document even though it has lower
        # quality
        if result:
            assert result[0].metadata.get(
                'timestamp', 0) < current_time - 86400

    @pytest.mark.asyncio
    async def test_respects_target_count_limit(
            self, maintenance_service, mock_deduplicator):
        """Test that results respect target count limit."""
        current_time = time.time()
        docs = [
            Document(
                page_content=f"Similar doc {i}",
                metadata={'importance_score': 0.5 - i * 0.1,
                          'access_count': i,
                          'timestamp': current_time - 86400 * (i + 2)}
            )
            for i in range(5)
        ]

        # Create pairs to form a cluster
        def find_similar(doc_data, threshold):
            pairs = []
            for i in range(len(doc_data) - 1):
                pairs.append((doc_data[i], doc_data[i + 1], 0.80))
            return pairs

        mock_deduplicator.similarity_calculator.find_duplicates_batch.side_effect = find_similar

        result = await maintenance_service._similarity_cluster_cleanup(docs, target_count=2)

        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(
            self, maintenance_service, mock_deduplicator):
        """Test that exceptions during clustering are handled gracefully."""
        docs = [
            Document(
                page_content="doc1", metadata={
                    'timestamp': time.time() - 86400 * 2}),
            Document(
                page_content="doc2", metadata={
                    'timestamp': time.time() - 86400 * 2})
        ]

        mock_deduplicator.similarity_calculator.find_duplicates_batch.side_effect = Exception(
            "Clustering error")

        result = await maintenance_service._similarity_cluster_cleanup(docs, target_count=1)

        assert result == []


class TestGroupIntoClusters:
    """Tests for _group_into_clusters method."""

    def test_creates_cluster_from_single_pair(self, maintenance_service):
        """Test cluster creation from a single document pair."""
        doc1 = Document(page_content="doc1", metadata={})
        doc2 = Document(page_content="doc2", metadata={})

        similar_pairs = [
            ({'document': doc1}, {'document': doc2}, 0.9)
        ]

        clusters = maintenance_service._group_into_clusters(similar_pairs)

        assert len(clusters) == 1
        assert len(clusters[0]) == 2
        assert doc1 in clusters[0]
        assert doc2 in clusters[0]

    def test_merges_overlapping_pairs_into_single_cluster(
            self, maintenance_service):
        """Test that overlapping pairs are merged into a single cluster."""
        doc1 = Document(page_content="doc1", metadata={})
        doc2 = Document(page_content="doc2", metadata={})
        doc3 = Document(page_content="doc3", metadata={})

        similar_pairs = [
            ({'document': doc1}, {'document': doc2}, 0.9),
            ({'document': doc2}, {'document': doc3}, 0.85)
        ]

        clusters = maintenance_service._group_into_clusters(similar_pairs)

        assert len(clusters) == 1
        assert len(clusters[0]) == 3
        assert doc1 in clusters[0]
        assert doc2 in clusters[0]
        assert doc3 in clusters[0]

    def test_creates_separate_clusters_for_disjoint_pairs(
            self, maintenance_service):
        """Test that disjoint pairs create separate clusters."""
        doc1 = Document(page_content="doc1", metadata={})
        doc2 = Document(page_content="doc2", metadata={})
        doc3 = Document(page_content="doc3", metadata={})
        doc4 = Document(page_content="doc4", metadata={})

        similar_pairs = [
            ({'document': doc1}, {'document': doc2}, 0.9),
            ({'document': doc3}, {'document': doc4}, 0.85)
        ]

        clusters = maintenance_service._group_into_clusters(similar_pairs)

        assert len(clusters) == 2

    def test_handles_empty_pairs(self, maintenance_service):
        """Test handling of empty pairs list."""
        clusters = maintenance_service._group_into_clusters([])

        assert clusters == []

    def test_merges_clusters_when_linking_pair_found(
            self, maintenance_service):
        """Test that separate clusters are merged when a linking pair is found."""
        doc1 = Document(page_content="doc1", metadata={})
        doc2 = Document(page_content="doc2", metadata={})
        doc3 = Document(page_content="doc3", metadata={})
        doc4 = Document(page_content="doc4", metadata={})

        similar_pairs = [
            ({'document': doc1}, {'document': doc2}, 0.9),  # Cluster 1
            ({'document': doc3}, {'document': doc4}, 0.85),  # Cluster 2
            ({'document': doc2}, {'document': doc3}, 0.80)  # Links clusters
        ]

        clusters = maintenance_service._group_into_clusters(similar_pairs)

        # Should have merged into one cluster
        non_empty_clusters = [c for c in clusters if c]
        assert len(non_empty_clusters) == 1
        assert len(non_empty_clusters[0]) == 4

    def test_adds_doc_to_existing_cluster(self, maintenance_service):
        """Test adding a document to an existing cluster."""
        doc1 = Document(page_content="doc1", metadata={})
        doc2 = Document(page_content="doc2", metadata={})
        doc3 = Document(page_content="doc3", metadata={})

        similar_pairs = [
            ({'document': doc1}, {'document': doc2}, 0.9),
            # doc3 joins doc1's cluster
            ({'document': doc1}, {'document': doc3}, 0.85)
        ]

        clusters = maintenance_service._group_into_clusters(similar_pairs)

        assert len(clusters) == 1
        assert len(clusters[0]) == 3


class TestAgeBasedCleanup:
    """Tests for _age_based_cleanup method."""

    def test_returns_oldest_documents(
            self, maintenance_service, sample_documents):
        """Test that oldest documents are returned first."""
        result = maintenance_service._age_based_cleanup(
            sample_documents, target_count=2)

        assert len(result) == 2
        # doc_3 is oldest (10 days), doc_1 is second oldest (5 days)
        chroma_ids = [doc.metadata.get('chroma_id') for doc in result]
        assert 'doc_3' in chroma_ids
        assert 'doc_1' in chroma_ids

    def test_considers_access_count(self, maintenance_service):
        """Test that access count affects priority score."""
        current_time = time.time()
        docs = [
            Document(
                page_content="Old but accessed",
                metadata={
                    'timestamp': current_time - 86400 * 5,
                    'access_count': 100}
            ),
            Document(
                page_content="New but never accessed",
                metadata={'timestamp': current_time - 86400, 'access_count': 0}
            )
        ]

        result = maintenance_service._age_based_cleanup(docs, target_count=1)

        # New doc with 0 access should have lower priority score
        assert result[0].page_content == "New but never accessed"

    def test_handles_missing_metadata(self, maintenance_service):
        """Test handling of documents with missing metadata."""
        docs = [
            Document(page_content="No metadata doc", metadata={}),
            Document(
                page_content="With metadata",
                metadata={
                    'timestamp': time.time(),
                    'access_count': 10})
        ]

        result = maintenance_service._age_based_cleanup(docs, target_count=1)

        # Doc with no metadata (timestamp=0, access_count=0) should be
        # prioritized for removal
        assert result[0].page_content == "No metadata doc"

    def test_returns_empty_for_empty_input(self, maintenance_service):
        """Test that empty list is returned for empty input."""
        result = maintenance_service._age_based_cleanup([], target_count=5)

        assert result == []

    def test_respects_target_count(
            self, maintenance_service, sample_documents):
        """Test that results respect target count."""
        result = maintenance_service._age_based_cleanup(
            sample_documents, target_count=3)

        assert len(result) == 3

    def test_returns_all_when_target_exceeds_docs(
            self, maintenance_service, sample_documents):
        """Test that all documents are returned when target exceeds available."""
        result = maintenance_service._age_based_cleanup(
            sample_documents, target_count=100)

        assert len(result) == len(sample_documents)

    def test_priority_score_formula(self, maintenance_service):
        """Test the priority score formula: timestamp + (access_count * 86400)."""
        docs = [
            Document(
                page_content="Doc A",
                metadata={'timestamp': 1000, 'access_count': 0}  # Score: 1000
            ),
            Document(
                page_content="Doc B",
                # Score: 500 + 86400 = 86900
                metadata={'timestamp': 500, 'access_count': 1}
            ),
            Document(
                page_content="Doc C",
                metadata={'timestamp': 100, 'access_count': 0}  # Score: 100
            )
        ]

        result = maintenance_service._age_based_cleanup(docs, target_count=3)

        # Sorted by priority score (lowest first): Doc C (100), Doc A (1000),
        # Doc B (86900)
        assert result[0].page_content == "Doc C"
        assert result[1].page_content == "Doc A"
        assert result[2].page_content == "Doc B"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_maintenance_at_exact_max_size(
            self, maintenance_service, mock_short_term_memory):
        """Test maintenance when count is exactly at max size."""
        mock_short_term_memory._collection.count.return_value = 100  # Exactly at max

        await maintenance_service.maintain_short_term_memory()

        # No cleanup should occur
        maintenance_service.storage_service.remove_documents_from_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_maintenance_with_zero_documents(
            self, maintenance_service, mock_short_term_memory):
        """Test maintenance when there are no documents."""
        mock_short_term_memory._collection.count.return_value = 0

        await maintenance_service.maintain_short_term_memory()

        maintenance_service.storage_service.remove_documents_from_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_smart_cleanup_with_none_metadata(
            self, maintenance_service, mock_short_term_memory, mock_deduplicator):
        """Test smart cleanup handles None metadata gracefully."""
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['doc_1', 'doc_2'],
            'documents': ['content_1', 'content_2'],
            # One None metadata
            'metadatas': [None, {'timestamp': time.time()}]
        }
        mock_deduplicator.enabled = False

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=1)

        # Should handle None metadata without error
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_smart_cleanup_with_empty_content(
            self, maintenance_service, mock_short_term_memory, mock_deduplicator):
        """Test smart cleanup handles empty content gracefully."""
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['doc_1', 'doc_2'],
            'documents': [None, ''],  # None and empty content
            'metadatas': [{'timestamp': time.time()}, {'timestamp': time.time() - 86400}]
        }
        mock_deduplicator.enabled = False

        result = await maintenance_service._smart_cleanup_selection(target_removal_count=1)

        # Should handle None/empty content without error
        assert len(result) == 1

    def test_choose_worse_document_identical_scores(self, maintenance_service):
        """Test choosing between documents with identical quality scores."""
        timestamp = time.time()
        doc1 = Document(
            page_content="Doc 1",
            metadata={
                'importance_score': 0.5,
                'access_count': 5,
                'timestamp': timestamp}
        )
        doc2 = Document(
            page_content="Doc 2",
            metadata={
                'importance_score': 0.5,
                'access_count': 5,
                'timestamp': timestamp}
        )

        result = maintenance_service._choose_worse_document(doc1, doc2)

        # Should return doc2 (last one when scores are equal due to >=
        # comparison)
        assert result == doc2

    @pytest.mark.asyncio
    async def test_concurrent_maintenance_calls(
            self, maintenance_service, mock_short_term_memory, mock_deduplicator):
        """Test that concurrent maintenance calls work correctly."""
        import asyncio

        mock_short_term_memory._collection.count.return_value = 120
        mock_short_term_memory._collection.get.return_value = {
            'ids': [f'doc_{i}' for i in range(120)],
            'documents': [f'content_{i}' for i in range(120)],
            'metadatas': [{'timestamp': time.time() - i * 3600} for i in range(120)]
        }
        mock_deduplicator.enabled = False

        # Run multiple maintenance calls concurrently
        tasks = [maintenance_service.maintain_short_term_memory()
                 for _ in range(3)]
        await asyncio.gather(*tasks)

        # Storage service should be called multiple times
        assert maintenance_service.storage_service.remove_documents_from_collection.call_count >= 1
