import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.mcp_memory_server.memory.hierarchical import HierarchicalMemorySystem
from src.mcp_memory_server.memory.scorer import MemoryImportanceScorer

# Fixture for mock ChromaDB collections (separate instances)
@pytest.fixture
def mock_short_term_collection():
    mock_collection = Mock()
    mock_collection.add_documents = Mock(return_value=None) # Mock add_documents as regular function
    mock_collection.count.return_value = 0 # Default count
    mock_collection.similarity_search_with_score = Mock(return_value=[])
    # Make the collection object support comparison operations for maintenance logic
    mock_collection.__le__ = Mock(return_value=True)
    mock_collection.__lt__ = Mock(return_value=True)
    mock_collection.__gt__ = Mock(return_value=False)
    mock_collection.__ge__ = Mock(return_value=False)
    return mock_collection

@pytest.fixture
def mock_long_term_collection():
    mock_collection = Mock()
    mock_collection.add_documents = Mock(return_value=None) # Mock add_documents as regular function
    mock_collection.count.return_value = 0 # Default count
    mock_collection.similarity_search_with_score = Mock(return_value=[])
    # Make the collection object support comparison operations for maintenance logic
    mock_collection.__le__ = Mock(return_value=True)
    mock_collection.__lt__ = Mock(return_value=True)
    mock_collection.__gt__ = Mock(return_value=False)
    mock_collection.__ge__ = Mock(return_value=False)
    return mock_collection

@pytest.fixture
def mock_permanent_collection():
    mock_collection = Mock()
    mock_collection.add_documents = Mock(return_value=None) # Mock add_documents as regular function
    mock_collection.count.return_value = 0 # Default count
    mock_collection.similarity_search_with_score = Mock(return_value=[])
    # Make the collection object support comparison operations for maintenance logic
    mock_collection.__le__ = Mock(return_value=True)
    mock_collection.__lt__ = Mock(return_value=True)
    mock_collection.__gt__ = Mock(return_value=False)
    mock_collection.__ge__ = Mock(return_value=False)
    return mock_collection

# Fixture for HierarchicalMemorySystem with mocked dependencies
@pytest.fixture
def hierarchical_memory_system(mock_short_term_collection, mock_long_term_collection, mock_permanent_collection):
    db_config = {'persist_directory': '/tmp/test_chroma', 'collections': {'short_term': 'st', 'long_term': 'lt'}}
    embeddings_config = {'model_name': 'test_model'}
    memory_config = {
        'short_term_max_size': 100,
        'short_term_threshold': 0.6, # Configurable threshold
        'long_term_threshold': 0.8   # Configurable threshold
    }
    scoring_config = {}
    deduplication_config = {'enabled': False}

    # Mock external dependencies
    with patch('src.mcp_memory_server.memory.hierarchical.Chroma', autospec=True) as MockChroma:
        with patch('src.mcp_memory_server.memory.hierarchical.HuggingFaceEmbeddings', autospec=True):
            with patch('src.mcp_memory_server.memory.hierarchical.MemoryImportanceScorer', autospec=True) as MockScorer:
                with patch('src.mcp_memory_server.memory.hierarchical.MemoryDeduplicator', autospec=True) as MockDeduplicator:
                    with patch('src.mcp_memory_server.memory.hierarchical.QueryPerformanceMonitor', autospec=True):
                        with patch('src.mcp_memory_server.memory.hierarchical.MemoryIntelligenceSystem', autospec=True):
                            with patch('src.mcp_memory_server.memory.hierarchical.ChunkRelationshipManager', autospec=True) as MockChunkManager:

                                # Configure MockChroma to return different mock collections
                                def chroma_side_effect(*args, **kwargs):
                                    collection_name = kwargs.get('collection_name', '')
                                    if 'short' in collection_name or 'st' in collection_name:
                                        return mock_short_term_collection
                                    elif 'long' in collection_name or 'lt' in collection_name:
                                        return mock_long_term_collection
                                    elif 'perm' in collection_name:
                                        return mock_permanent_collection
                                    else:
                                        return mock_short_term_collection  # Default
                                
                                MockChroma.side_effect = chroma_side_effect

                                # Configure MockScorer to return a mock instance
                                mock_scorer_instance = MockScorer.return_value
                                mock_scorer_instance.calculate_importance.return_value = 0.5 # Default importance

                                # Configure MockDeduplicator to return a mock instance with enabled attribute
                                mock_deduplicator_instance = MockDeduplicator.return_value
                                mock_deduplicator_instance.enabled = deduplication_config['enabled']
                                mock_deduplicator_instance.check_ingestion_duplicates = Mock(return_value=('add', None, 0.0))
                                mock_deduplicator_instance.boost_existing_document = Mock(return_value={'updated': True})

                                # Configure MockChunkManager to return AsyncMock for create_document_with_relationships
                                mock_chunk_manager_instance = MockChunkManager.return_value
                                mock_chunk_manager_instance.create_document_with_relationships = AsyncMock(
                                    return_value=[Mock(page_content="test", metadata={"chunk_id": "test_chunk"})]
                                )

                                hms = HierarchicalMemorySystem(
                                    db_config=db_config,
                                    embeddings_config=embeddings_config,
                                    memory_config=memory_config,
                                    scoring_config=scoring_config,
                                    deduplication_config=deduplication_config
                                )
                                hms.importance_scorer = mock_scorer_instance # Ensure our mock is used
                                hms.deduplicator = mock_deduplicator_instance # Ensure our mock is used
                                hms.short_term_memory = mock_short_term_collection # Ensure our mock is used
                                hms.long_term_memory = mock_long_term_collection # Ensure our mock is used
                                hms.permanent_memory = mock_permanent_collection # Ensure our mock is used
                                return hms


@pytest.mark.asyncio
async def test_add_memory_routes_to_short_term(hierarchical_memory_system):
    """Test that documents with importance below short_term_threshold go to short_term memory."""
    hierarchical_memory_system.importance_scorer.calculate_importance.return_value = 0.5 # Below 0.6
    
    result = await hierarchical_memory_system.add_memory("test content")
    
    assert result['success'] is True
    assert result['collection'] == "short_term"
    hierarchical_memory_system.short_term_memory.add_documents.assert_called_once()
    hierarchical_memory_system.long_term_memory.add_documents.assert_not_called()

@pytest.mark.asyncio
async def test_add_memory_routes_to_long_term(hierarchical_memory_system):
    """Test that documents with importance above long_term_threshold go to long_term memory."""
    hierarchical_memory_system.importance_scorer.calculate_importance.return_value = 0.85 # Above 0.8
    
    result = await hierarchical_memory_system.add_memory("test content")
    
    assert result['success'] is True
    assert result['collection'] == "long_term"
    hierarchical_memory_system.long_term_memory.add_documents.assert_called_once()
    hierarchical_memory_system.short_term_memory.add_documents.assert_not_called()

@pytest.mark.asyncio
async def test_add_memory_routes_to_permanent(hierarchical_memory_system):
    """Test that documents with importance above long_term_threshold go to long_term memory (acting as permanent)."""
    # Note: The current implementation routes > long_term_threshold to long_term. 
    # A true permanent tier would need a separate Chroma collection.
    hierarchical_memory_system.importance_scorer.calculate_importance.return_value = 0.9 # Above 0.8
    
    result = await hierarchical_memory_system.add_memory("test content")
    
    assert result['success'] is True
    assert result['collection'] == "long_term"
    hierarchical_memory_system.long_term_memory.add_documents.assert_called_once()
    hierarchical_memory_system.short_term_memory.add_documents.assert_not_called()

@pytest.mark.asyncio 
async def test_add_memory_handles_db_error(hierarchical_memory_system):
    """Test that add_memory gracefully handles database errors."""
    # Mock the add_documents method to raise an exception
    def failing_add_documents(*args, **kwargs):
        raise Exception("DB write error")
    
    hierarchical_memory_system.short_term_memory.add_documents = failing_add_documents
    hierarchical_memory_system.importance_scorer.calculate_importance.return_value = 0.5
    
    # Mock collection count to avoid maintenance comparison issues
    hierarchical_memory_system.short_term_memory._collection = Mock()
    hierarchical_memory_system.short_term_memory._collection.count.return_value = 100
    
    result = await hierarchical_memory_system.add_memory("test content")
    
    assert result['success'] is False
    assert "DB write error" in result['message']

@pytest.mark.asyncio
async def test_add_memory_deduplication_boost_existing(hierarchical_memory_system):
    """Test add_memory with deduplication boosting an existing document."""
    hierarchical_memory_system.deduplicator.enabled = True
    # Mock as AsyncMock since check_ingestion_duplicates is now async
    hierarchical_memory_system.deduplicator.check_ingestion_duplicates = AsyncMock(
        return_value=('boost_existing', {'metadata': {'chunk_id': 'existing_id'}}, 0.95)
    )
    hierarchical_memory_system.deduplicator.boost_existing_document.return_value = {'updated': True}

    result = await hierarchical_memory_system.add_memory("duplicate content")

    assert result['success'] is True
    assert result['action'] == "boosted_existing"
    hierarchical_memory_system.deduplicator.check_ingestion_duplicates.assert_called_once()
    hierarchical_memory_system.deduplicator.boost_existing_document.assert_called_once()
    hierarchical_memory_system.short_term_memory.add_documents.assert_not_called()

@pytest.mark.asyncio
async def test_add_memory_deduplication_merge_content(hierarchical_memory_system):
    """Test add_memory with deduplication suggesting content merge (and still adding)."""
    hierarchical_memory_system.deduplicator.enabled = True
    # Mock as AsyncMock since check_ingestion_duplicates is now async
    hierarchical_memory_system.deduplicator.check_ingestion_duplicates = AsyncMock(
        return_value=('merge_content', {'metadata': {'chunk_id': 'existing_id'}}, 0.88)
    )

    result = await hierarchical_memory_system.add_memory("content to merge")

    assert result['success'] is True
    assert result['action'] == "added"
    hierarchical_memory_system.deduplicator.check_ingestion_duplicates.assert_called_once()
    hierarchical_memory_system.short_term_memory.add_documents.assert_called_once()

@pytest.mark.asyncio
async def test_add_memory_deduplication_add_new(hierarchical_memory_system):
    """Test add_memory with deduplication suggesting add_new."""
    hierarchical_memory_system.deduplicator.enabled = True
    # Mock as AsyncMock since check_ingestion_duplicates is now async
    hierarchical_memory_system.deduplicator.check_ingestion_duplicates = AsyncMock(
        return_value=('add_new', None, 0.0)
    )

    result = await hierarchical_memory_system.add_memory("truly new content")

    assert result['success'] is True
    assert result['action'] == "added"
    hierarchical_memory_system.deduplicator.check_ingestion_duplicates.assert_called_once()
    hierarchical_memory_system.short_term_memory.add_documents.assert_called_once()

# Consolidated memory tier has been removed from the roadmap

@pytest.mark.asyncio
async def test_add_memory_empty_content(hierarchical_memory_system):
    """Test add_memory with empty content - system should handle gracefully."""
    hierarchical_memory_system.importance_scorer.calculate_importance.return_value = 0.3
    hierarchical_memory_system.short_term_memory._collection = Mock()
    hierarchical_memory_system.short_term_memory._collection.count.return_value = 50
    
    result = await hierarchical_memory_system.add_memory("")
    
    # System should handle empty content gracefully (could be metadata-only memory)
    assert result['success'] is True
    assert result['collection'] == "short_term"
    hierarchical_memory_system.short_term_memory.add_documents.assert_called_once()

@pytest.mark.asyncio
async def test_add_memory_invalid_memory_type(hierarchical_memory_system):
    """Test add_memory with an invalid memory_type."""
    # The current implementation defaults to short_term if type is not 'long_term' or 'auto'
    # So this is more of an edge case for unexpected input, but should not fail.
    result = await hierarchical_memory_system.add_memory("content", memory_type="invalid_type")
    assert result['success'] is True
    assert result['collection'] == "short_term"

@pytest.mark.asyncio
async def test_query_memories_empty_query(hierarchical_memory_system):
    """Test query_memories with an empty query."""
    result = await hierarchical_memory_system.query_memories("")
    assert result['content'] == []
    assert result['total_results'] == 0

@pytest.mark.asyncio
async def test_query_memories_invalid_collection(hierarchical_memory_system):
    """Test query_memories with an invalid collection name."""
    result = await hierarchical_memory_system.query_memories("query", collections=["non_existent_collection"])
    assert result['content'] == []
    assert result['total_results'] == 0