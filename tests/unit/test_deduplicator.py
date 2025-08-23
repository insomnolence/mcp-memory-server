import pytest
from unittest.mock import Mock, patch
import numpy as np

# Assuming the following imports are correct based on project structure
from src.mcp_memory_server.deduplication.deduplicator import MemoryDeduplicator
from src.mcp_memory_server.deduplication.similarity import SimilarityCalculator

# Fixture for a simple embedding model mock
@pytest.fixture
def mock_embedding_model():
    mock_model = Mock()
    # Mock a consistent embedding for a given text for testing purposes
    def get_embedding_side_effect(text):
        if "apple" in text:
            return np.array([0.1, 0.2, 0.3])
        elif "orange" in text:
            return np.array([0.15, 0.25, 0.35])
        elif "fruit" in text:
            return np.array([0.12, 0.22, 0.32])
        elif "car" in text:
            return np.array([0.9, 0.8, 0.7])
        else:
            return np.random.rand(3) # Random for other texts
    mock_model.encode.side_effect = get_embedding_side_effect
    return mock_model

# Fixture for SimilarityCalculator
@pytest.fixture
def similarity_calculator():
    return SimilarityCalculator(similarity_threshold=0.8)

# Fixture for MemoryDeduplicator
@pytest.fixture
def memory_deduplicator(mock_embedding_model):
    # Mock chunk_manager and advanced_features as they are external dependencies
    mock_chunk_manager = Mock()
    mock_advanced_features = Mock()
    mock_advanced_features.apply_domain_aware_thresholds.return_value = [(0.8, 'default')]
    mock_advanced_features.apply_semantic_clustering.return_value = {'clusters': {}}

    with patch('src.mcp_memory_server.deduplication.deduplicator.SimilarityCalculator', autospec=True) as MockSimilarityCalculator:
        # Ensure the mocked SimilarityCalculator is used by Deduplicator
        mock_sim_calc_instance = MockSimilarityCalculator.return_value
        mock_sim_calc_instance.calculate_similarity.side_effect = lambda e1, e2: np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
        mock_sim_calc_instance.find_duplicates_batch.return_value = [] # Default mock behavior

        deduplicator = MemoryDeduplicator(
            deduplication_config={'enabled': True, 'similarity_threshold': 0.8},
            chunk_manager=mock_chunk_manager
        )
        # Manually set the mocked advanced_features after initialization
        deduplicator.advanced_features = mock_advanced_features
        deduplicator.similarity_calculator = mock_sim_calc_instance # Ensure it uses our mock
        return deduplicator


class TestSimilarityCalculator:

    def test_calculate_similarity(self, similarity_calculator):
        emb1 = np.array([1.0, 0.0])
        emb2 = np.array([0.9, 0.1])
        emb3 = np.array([-1.0, 0.0])

        assert similarity_calculator.calculate_similarity(emb1, emb1) == pytest.approx(1.0)
        # Calculate the expected cosine similarity manually for better accuracy
        expected_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        assert similarity_calculator.calculate_similarity(emb1, emb2) == pytest.approx(expected_sim, rel=1e-3)
        assert similarity_calculator.calculate_similarity(emb1, emb3) == pytest.approx(-1.0)

    def test_find_duplicates_batch_no_duplicates(self, similarity_calculator, mock_embedding_model):
        docs = [
            {'id': '1', 'page_content': 'apple', 'embedding': mock_embedding_model.encode('apple')},
            {'id': '2', 'page_content': 'car', 'embedding': mock_embedding_model.encode('car')},
        ]
        duplicates = similarity_calculator.find_duplicates_batch(docs, threshold=0.9)
        assert len(duplicates) == 0

    def test_find_duplicates_batch_with_duplicates(self, similarity_calculator, mock_embedding_model):
        # Create two very similar documents and one very different one
        emb_fruit1 = np.array([1.0, 0.0, 0.0])  # apple embedding
        emb_fruit2 = np.array([0.95, 0.05, 0.0])  # green apple embedding (very similar)
        emb_car = np.array([0.0, 1.0, 0.0])  # car embedding (orthogonal, very different)

        docs = [
            {'id': '1', 'page_content': 'a red apple', 'embedding': emb_fruit1},
            {'id': '2', 'page_content': 'a green apple', 'embedding': emb_fruit2},
            {'id': '3', 'page_content': 'a fast car', 'embedding': emb_car},
        ]
        
        duplicates = similarity_calculator.find_duplicates_batch(docs, threshold=0.9)
        
        # The apple embeddings should be similar enough to be detected as duplicates
        expected_sim = similarity_calculator.calculate_similarity(emb_fruit1, emb_fruit2)
        assert expected_sim >= 0.9  # Ensure our test embeddings are actually similar
        
        # Should find exactly one duplicate pair (the two apple embeddings)
        assert len(duplicates) == 1
        duplicate_pair = duplicates[0]
        assert duplicate_pair[0]['id'] in ['1', '2']
        assert duplicate_pair[1]['id'] in ['1', '2'] 
        assert duplicate_pair[0]['id'] != duplicate_pair[1]['id']  # Different IDs
        assert duplicate_pair[2] == pytest.approx(expected_sim, rel=1e-3)


class TestMemoryDeduplicator:

    def test_check_ingestion_duplicates_no_duplicates(self, memory_deduplicator):
        mock_collection = Mock()
        mock_collection.similarity_search.return_value = []
        action, existing_doc, similarity = memory_deduplicator.check_ingestion_duplicates(
            "new unique content", {'chunk_id': 'new_id'}, mock_collection
        )
        assert action == 'add_new'
        assert existing_doc is None
        assert similarity == 0.0

    def test_check_ingestion_duplicates_boost_existing(self, memory_deduplicator, mock_embedding_model):
        mock_collection = Mock()
        # Mock a candidate that is very similar
        candidate_doc = Mock()
        candidate_doc.page_content = "existing similar content"
        candidate_doc.metadata = {'chunk_id': 'existing_id', 'importance_score': 0.5}
        mock_collection.similarity_search.return_value = [candidate_doc]

        # Mock the internal _simple_content_similarity to return a high score
        with patch.object(memory_deduplicator, '_simple_content_similarity', return_value=0.98):
            action, existing_doc, similarity = memory_deduplicator.check_ingestion_duplicates(
                "new similar content", {'chunk_id': 'new_id'}, mock_collection
            )
            assert action == 'boost_existing'
            assert existing_doc is not None
            assert existing_doc['id'] == 'existing_id'
            assert similarity == pytest.approx(0.98)

    def test_deduplicate_collection_no_docs(self, memory_deduplicator):
        mock_collection = Mock()
        mock_collection.similarity_search.return_value = []
        results = memory_deduplicator.deduplicate_collection(mock_collection)
        assert results['message'] == 'Not enough documents for deduplication'

    def test_deduplicate_collection_no_duplicates_found(self, memory_deduplicator, mock_embedding_model):
        mock_collection = Mock()
        docs = [
            Mock(page_content='doc1', metadata={'chunk_id': '1'}),
            Mock(page_content='doc2', metadata={'chunk_id': '2'}),
        ]
        mock_collection.similarity_search.return_value = docs

        # Ensure _find_duplicates_advanced returns no duplicates
        with patch.object(memory_deduplicator, '_find_duplicates_advanced', return_value=[]):
            results = memory_deduplicator.deduplicate_collection(mock_collection)
            assert results['message'] == 'No duplicates found'
            assert results['duplicates_found'] == 0

    def test_deduplicate_collection_with_duplicates_dry_run(self, memory_deduplicator, mock_embedding_model):
        mock_collection = Mock()
        doc1 = Mock(page_content='apple', metadata={'chunk_id': '1'})
        doc2 = Mock(page_content='apple_similar', metadata={'chunk_id': '2'})
        mock_collection.similarity_search.return_value = [doc1, doc2]

        # Mock _find_duplicates_advanced to return a duplicate pair
        mock_duplicate_pair = ({'id': '1', 'page_content': 'apple'}, {'id': '2', 'page_content': 'apple_similar'}, 0.95)
        with patch.object(memory_deduplicator, '_find_duplicates_advanced', return_value=[mock_duplicate_pair]):
            results = memory_deduplicator.deduplicate_collection(mock_collection, dry_run=True)
            assert results['duplicates_found'] == 1
            assert results['message'].startswith('DRY RUN')
            assert len(results['duplicate_pairs']) == 1
            assert results['duplicate_pairs'][0]['doc1_id'] == '1'

    def test_deduplicate_collection_with_duplicates_merge(self, memory_deduplicator, mock_embedding_model):
        mock_collection = Mock()
        doc1 = Mock(page_content='apple', metadata={'chunk_id': '1'})
        doc2 = Mock(page_content='apple_similar', metadata={'chunk_id': '2'})
        mock_collection.similarity_search.return_value = [doc1, doc2]

        # Mock _find_duplicates_advanced to return a duplicate pair
        mock_duplicate_pair = ({'id': '1', 'page_content': 'apple'}, {'id': '2', 'page_content': 'apple_similar'}, 0.95)
        with patch.object(memory_deduplicator, '_find_duplicates_advanced', return_value=[mock_duplicate_pair]):
            # Mock the document_merger.batch_merge_duplicates
            with patch.object(memory_deduplicator.document_merger, 'batch_merge_duplicates', return_value=[{'id': 'merged_doc'}]) as mock_merge:
                results = memory_deduplicator.deduplicate_collection(mock_collection, dry_run=False)
                assert results['merged_documents'] == 1
                assert results['message'].startswith('Merged')
                mock_merge.assert_called_once()
                assert memory_deduplicator.stats['total_duplicates_found'] == 1
                assert memory_deduplicator.stats['total_documents_merged'] == 1
