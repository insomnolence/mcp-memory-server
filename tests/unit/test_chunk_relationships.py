import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.mcp_memory_server.memory.chunk_relationships import ChunkRelationshipManager
from langchain_core.documents import Document

# Fixture for a mock HierarchicalMemorySystem


@pytest.fixture
def mock_memory_system():
    mock_system = Mock()
    mock_system.short_term_memory = Mock()
    mock_system.long_term_memory = Mock()
    mock_system.permanent_memory = Mock()
    # Mock query_memories as async method
    mock_system.query_memories = AsyncMock(return_value={'content': []})
    return mock_system

# Fixture for ChunkRelationshipManager configuration


@pytest.fixture
def chunk_manager_config():
    return {
        'enabled': True,
        'max_relationships_per_chunk': 5,
        'semantic_similarity_threshold': 0.8,
        'co_occurrence_window': 3,
        'enable_related_retrieval': True,
        'max_related_chunks': 3,
        'relationship_decay_days': 30,
        'track_merge_relationships': True,
        'preserve_original_context': True,
        'context_window_size': 2,
        'semantic_relationship_threshold': 0.7
    }

# Fixture for ChunkRelationshipManager instance


@pytest.fixture
def chunk_relationship_manager(mock_memory_system, chunk_manager_config):
    # Mock the deduplicator's similarity_calculator for semantic checks
    mock_deduplicator = Mock()
    mock_deduplicator.similarity_calculator = Mock()
    mock_deduplicator.similarity_calculator.calculate_similarity.return_value = 0.9  # Default high similarity
    mock_deduplicator.similarity_calculator.find_similar_candidates.return_value = []

    # Patch the HierarchicalMemorySystem to return our mock deduplicator
    patch_target = 'src.mcp_memory_server.memory.services.facade.HierarchicalMemorySystem'
    with patch(patch_target, return_value=mock_memory_system):
        manager = ChunkRelationshipManager(mock_memory_system, chunk_manager_config)
        manager.memory_system.deduplicator = mock_deduplicator  # Inject mock deduplicator
        return manager


class TestChunkRelationshipManager:

    @pytest.mark.asyncio
    async def test_create_document_with_relationships(self, chunk_relationship_manager):
        content = "This is a test document with multiple sentences. It talks about apples and oranges."
        metadata = {'source': 'test', 'timestamp': 123}
        chunks = ["This is a test document.", "It talks about apples and oranges."]
        memory_id = "mem_123"
        collection_name = "short_term"

        documents = await chunk_relationship_manager.create_document_with_relationships(
            content, metadata, chunks, memory_id, collection_name
        )

        assert len(documents) == len(chunks)
        for i, doc in enumerate(documents):
            assert isinstance(doc, Document)
            assert doc.page_content == chunks[i]
            assert doc.metadata['source'] == 'test'
            assert doc.metadata['memory_id'] == memory_id
            assert doc.metadata['collection_name'] == collection_name
            assert doc.metadata['chunk_index'] == i
            assert 'chunk_id' in doc.metadata
            # Note: 'relationships' field is now stored in internal relationship manager, not ChromaDB metadata
            assert 'chunk_id' in doc.metadata  # Should have chunk_id for relationship tracking

    def test_retrieve_related_chunks_no_relationships(self, chunk_relationship_manager):
        # Mock a document with no relationships
        doc_id = "chunk_abc"
        chunk_relationship_manager.memory_system.short_term_memory.get.return_value = {
            'ids': [doc_id],
            'documents': ["content"],
            'metadatas': [{'chunk_id': doc_id}]  # 'relationships' no longer in ChromaDB metadata
        }

        related = chunk_relationship_manager.retrieve_related_chunks(doc_id)
        assert len(related) == 0

    def test_retrieve_related_chunks_semantic_relationship(self, chunk_relationship_manager):
        # Mock two chunks with a semantic relationship
        chunk_id1 = "chunk_1"
        chunk_id2 = "chunk_2"
        content1 = "apple is a fruit"
        content2 = "orange is a citrus"

        # Mock the get method to return documents with relationships
        chunk_relationship_manager.memory_system.short_term_memory.get.return_value = {
            'ids': [chunk_id1, chunk_id2],
            'documents': [content1, content2],
            'metadatas': [
                {'chunk_id': chunk_id1},  # 'relationships' no longer in ChromaDB metadata
                {'chunk_id': chunk_id2}
            ]
        }

        # Mock the similarity search to return the related document
        chunk_relationship_manager.memory_system.short_term_memory.similarity_search_with_score.return_value = [
            (Document(page_content=content2, metadata={'chunk_id': chunk_id2}), 0.1)  # distance
        ]

        # Set up internal relationship data to simulate the relationship
        chunk_relationship_manager.chunk_relationships[chunk_id1] = {
            'chunk_id': chunk_id1,
            'document_id': 'test_doc_1',
            'chunk_index': 0,
            'content_preview': content1[:100],
            'related_chunks': [
                {
                    'target_chunk_id': chunk_id2,
                    'type': 'semantic_similarity',
                    'score': 0.9,
                    'context_relevance': 0.8
                }
            ],
            'deduplication_sources': [],
            'access_history': [],
            'relationship_strength': {},
            'complex_relationships': {}
        }

        # Also set up target chunk in relationships for completeness
        chunk_relationship_manager.chunk_relationships[chunk_id2] = {
            'chunk_id': chunk_id2,
            'document_id': 'test_doc_2',
            'chunk_index': 0,
            'content_preview': content2[:100],
            'related_chunks': [],
            'deduplication_sources': [],
            'access_history': [],
            'relationship_strength': {},
            'complex_relationships': {}
        }

        related = chunk_relationship_manager.retrieve_related_chunks(chunk_id1)
        assert len(related) == 1
        assert related[0]['chunk_id'] == chunk_id2
        assert related[0]['relationship_type'] == 'semantic_similarity'
        assert related[0]['content_preview'] == content2

    @pytest.mark.asyncio
    async def test_update_relationships_semantic(self, chunk_relationship_manager):
        # Mock a document and a candidate for semantic relationship
        doc = Document(page_content="apple fruit", metadata={'chunk_id': 'doc1'})
        candidate = Document(page_content="orange fruit", metadata={'chunk_id': 'doc2'})

        # Mock the similarity calculator to return a high similarity
        sim_calc = chunk_relationship_manager.memory_system.deduplicator.similarity_calculator
        sim_calc.calculate_similarity.return_value = 0.9

        # Mock the update_document_metadata method (now async) and initialize chunk_relationships
        chunk_relationship_manager.memory_system.update_document_metadata = AsyncMock(return_value={'success': True})
        chunk_relationship_manager.chunk_relationships['doc1'] = {'related_chunks': []}

        await chunk_relationship_manager._update_relationships_semantic(doc, [candidate], 'short_term')

        # Assert that the relationship has been added to internal relationship manager
        chunk_id = 'doc1'
        assert chunk_id in chunk_relationship_manager.chunk_relationships
        chunk_rel = chunk_relationship_manager.chunk_relationships[chunk_id]
        assert 'related_chunks' in chunk_rel
        assert len(chunk_rel['related_chunks']) == 1
        assert chunk_rel['related_chunks'][0]['target_chunk_id'] == 'doc2'
        assert chunk_rel['related_chunks'][0]['type'] == 'semantic_similarity'

    @pytest.mark.asyncio
    async def test_update_relationships_co_occurrence(self, chunk_relationship_manager):
        # Mock a list of documents for co-occurrence
        docs = [
            Document(page_content="apple and banana", metadata={'chunk_id': 'doc1'}),
            Document(page_content="banana and orange", metadata={'chunk_id': 'doc2'}),
            Document(page_content="grape and kiwi", metadata={'chunk_id': 'doc3'})
        ]

        # Mock the update_document_metadata method (now async) and initialize chunk_relationships
        chunk_relationship_manager.memory_system.update_document_metadata = AsyncMock(return_value={'success': True})
        chunk_relationship_manager.chunk_relationships['doc1'] = {'related_chunks': []}
        chunk_relationship_manager.chunk_relationships['doc2'] = {'related_chunks': []}

        await chunk_relationship_manager._update_relationships_co_occurrence(docs, 'short_term')

        # Assert that relationships are added for doc1 and doc2 (co-occurrence of 'banana')
        assert 'doc1' in chunk_relationship_manager.chunk_relationships
        doc1_rel = chunk_relationship_manager.chunk_relationships['doc1']
        assert 'related_chunks' in doc1_rel
        assert any(rel['target_chunk_id'] == 'doc2' and rel['type'] ==
                   'co_occurrence' for rel in doc1_rel['related_chunks'])

    def test_get_relationship_statistics(self, chunk_relationship_manager):
        # Mock the _collection.get() method which is what the actual code calls
        chunk_relationship_manager.memory_system.short_term_memory._collection.get.return_value = {
            'ids': ['c1', 'c2'],
            'documents': ['content1', 'content2'],
            'metadatas': [
                {'chunk_id': 'c1'},  # 'relationships' no longer in ChromaDB metadata
                {'chunk_id': 'c2'}
            ]
        }

        # Set up internal relationship data
        chunk_relationship_manager.chunk_relationships['c1'] = {
            'related_chunks': [{'type': 'semantic_similarity', 'score': 0.9}]
        }
        chunk_relationship_manager.chunk_relationships['c2'] = {
            'related_chunks': []
        }
        chunk_relationship_manager.memory_system.long_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }

        stats = chunk_relationship_manager.get_relationship_statistics()

        assert 'total_chunks_analyzed' in stats
        assert stats['total_chunks_analyzed'] == 2
        assert 'total_relationships_found' in stats
        assert stats['total_relationships_found'] == 1
        assert 'relationship_types_distribution' in stats
        assert stats['relationship_types_distribution'] == {'semantic_similarity': 1}
