"""
Unit tests for Relationship Persistence

Tests the serialization, deserialization, and persistence of:
- Chunk relationships (semantic, co-occurrence)
- Document deduplication history
- Merge history via system documents
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

from src.mcp_memory_server.memory.chunk_relationships import (
    ChunkRelationshipManager,
    SYSTEM_DOC_TYPE_MERGE_HISTORY,
    FIELD_RELATED_CHUNKS,
    FIELD_DEDUP_SOURCES,
    FIELD_RELATIONSHIP_STRENGTH,
    FIELD_DEDUP_HISTORY,
    MAX_MERGE_HISTORY_SIZE,
    MAX_RELATIONSHIPS_PER_CHUNK,
)


@pytest.fixture
def mock_memory_system():
    """Create a mock HierarchicalMemorySystem."""
    mock_system = Mock()
    mock_system.short_term_memory = Mock()
    mock_system.long_term_memory = Mock()
    mock_system.short_term_memory._collection = Mock()
    mock_system.long_term_memory._collection = Mock()
    mock_system.query_memories = AsyncMock(return_value={'content': []})
    mock_system.update_document_metadata = AsyncMock(return_value={'success': True})
    
    # Default empty responses
    mock_system.short_term_memory._collection.get.return_value = {
        'ids': [], 'documents': [], 'metadatas': []
    }
    mock_system.long_term_memory._collection.get.return_value = {
        'ids': [], 'documents': [], 'metadatas': []
    }
    
    return mock_system


@pytest.fixture
def chunk_manager(mock_memory_system):
    """Create a ChunkRelationshipManager with mocked dependencies."""
    mock_deduplicator = Mock()
    mock_deduplicator.similarity_calculator = Mock()
    mock_deduplicator.similarity_calculator.calculate_similarity.return_value = 0.9
    
    manager = ChunkRelationshipManager(mock_memory_system)
    manager.memory_system.deduplicator = mock_deduplicator
    return manager


class TestSerializationHelpers:
    """Tests for JSON serialization/deserialization helpers."""

    def test_serialize_json_list(self, chunk_manager):
        """Test serializing a list to JSON."""
        data = [{'key': 'value'}, {'number': 42}]
        result = chunk_manager._serialize_json(data)
        assert result == json.dumps(data)

    def test_serialize_json_dict(self, chunk_manager):
        """Test serializing a dict to JSON."""
        data = {'key': 'value', 'nested': {'inner': True}}
        result = chunk_manager._serialize_json(data)
        assert result == json.dumps(data)

    def test_serialize_json_handles_error(self, chunk_manager):
        """Test that serialization errors return safe defaults."""
        # Create an object that can't be JSON serialized
        class NonSerializable:
            pass
        
        data = [NonSerializable()]
        result = chunk_manager._serialize_json(data)
        assert result == '[]'  # Default for list

    def test_deserialize_json_valid(self, chunk_manager):
        """Test deserializing valid JSON."""
        json_str = '[{"key": "value"}]'
        result = chunk_manager._deserialize_json(json_str)
        assert result == [{'key': 'value'}]

    def test_deserialize_json_empty_string(self, chunk_manager):
        """Test deserializing empty string returns default."""
        result = chunk_manager._deserialize_json('', default=[])
        assert result == []

    def test_deserialize_json_none(self, chunk_manager):
        """Test deserializing None returns default."""
        result = chunk_manager._deserialize_json(None, default={})
        assert result == {}

    def test_deserialize_json_invalid(self, chunk_manager):
        """Test deserializing invalid JSON returns default."""
        result = chunk_manager._deserialize_json('not valid json', default=[])
        assert result == []


class TestChunkRelationshipSerialization:
    """Tests for chunk relationship serialization."""

    def test_serialize_chunk_relationships_with_data(self, chunk_manager):
        """Test serializing chunk relationships to metadata."""
        chunk_id = 'test_chunk_1'
        chunk_manager.chunk_relationships[chunk_id] = {
            'chunk_id': chunk_id,
            'related_chunks': [
                {'target_chunk_id': 'chunk_2', 'type': 'semantic', 'score': 0.85}
            ],
            'deduplication_sources': [
                {'original_document': 'doc_1', 'merge_timestamp': 1234567890}
            ],
            'relationship_strength': {'chunk_2': 0.9}
        }

        result = chunk_manager._serialize_chunk_relationships(chunk_id)

        assert FIELD_RELATED_CHUNKS in result
        assert FIELD_DEDUP_SOURCES in result
        assert FIELD_RELATIONSHIP_STRENGTH in result
        
        # Verify JSON is valid
        related = json.loads(result[FIELD_RELATED_CHUNKS])
        assert len(related) == 1
        assert related[0]['target_chunk_id'] == 'chunk_2'

    def test_serialize_chunk_relationships_empty(self, chunk_manager):
        """Test serializing chunk with no relationships returns empty dict."""
        chunk_id = 'empty_chunk'
        chunk_manager.chunk_relationships[chunk_id] = {
            'chunk_id': chunk_id,
            'related_chunks': [],
            'deduplication_sources': [],
            'relationship_strength': {}
        }

        result = chunk_manager._serialize_chunk_relationships(chunk_id)
        assert result == {}

    def test_serialize_chunk_relationships_not_found(self, chunk_manager):
        """Test serializing non-existent chunk returns empty dict."""
        result = chunk_manager._serialize_chunk_relationships('nonexistent')
        assert result == {}

    def test_serialize_limits_relationships(self, chunk_manager):
        """Test that serialization limits the number of relationships."""
        chunk_id = 'many_relationships'
        many_relationships = [
            {'target_chunk_id': f'chunk_{i}', 'type': 'semantic', 'score': 0.5}
            for i in range(MAX_RELATIONSHIPS_PER_CHUNK + 10)
        ]
        chunk_manager.chunk_relationships[chunk_id] = {
            'related_chunks': many_relationships,
            'deduplication_sources': [],
            'relationship_strength': {}
        }

        result = chunk_manager._serialize_chunk_relationships(chunk_id)
        related = json.loads(result[FIELD_RELATED_CHUNKS])
        assert len(related) == MAX_RELATIONSHIPS_PER_CHUNK


class TestChunkRelationshipDeserialization:
    """Tests for chunk relationship deserialization."""

    def test_deserialize_chunk_relationships_with_data(self, chunk_manager):
        """Test deserializing metadata back to relationships."""
        metadata = {
            FIELD_RELATED_CHUNKS: '[{"target_chunk_id": "chunk_2", "type": "semantic"}]',
            FIELD_DEDUP_SOURCES: '[{"original_document": "doc_1"}]',
            FIELD_RELATIONSHIP_STRENGTH: '{"chunk_2": 0.9}'
        }

        result = chunk_manager._deserialize_chunk_relationships(metadata)

        assert result['related_chunks'] == [{'target_chunk_id': 'chunk_2', 'type': 'semantic'}]
        assert result['deduplication_sources'] == [{'original_document': 'doc_1'}]
        assert result['relationship_strength'] == {'chunk_2': 0.9}

    def test_deserialize_chunk_relationships_empty_metadata(self, chunk_manager):
        """Test deserializing empty metadata returns defaults (backward compat)."""
        metadata = {}

        result = chunk_manager._deserialize_chunk_relationships(metadata)

        assert result['related_chunks'] == []
        assert result['deduplication_sources'] == []
        assert result['relationship_strength'] == {}

    def test_deserialize_chunk_relationships_partial_metadata(self, chunk_manager):
        """Test deserializing partial metadata (backward compat)."""
        metadata = {
            FIELD_RELATED_CHUNKS: '[{"target": "chunk_2"}]'
            # Missing other fields
        }

        result = chunk_manager._deserialize_chunk_relationships(metadata)

        assert result['related_chunks'] == [{'target': 'chunk_2'}]
        assert result['deduplication_sources'] == []
        assert result['relationship_strength'] == {}


class TestLoadChunkFromChromaDB:
    """Tests for lazy loading chunks with deserialized relationships."""

    def test_load_chunk_deserializes_relationships(self, chunk_manager, mock_memory_system):
        """Test that loading a chunk deserializes persisted relationships."""
        chunk_id = 'persisted_chunk'
        persisted_metadata = {
            'chunk_id': chunk_id,
            'document_id': 'doc_123',
            'chunk_index': 0,
            'previous_chunk': None,
            'next_chunk': 'doc_123_chunk_1',
            'document_start': True,
            'document_end': False,
            'relative_position': 0.0,
            'context_start_chunk': 0,
            'context_end_chunk': 2,
            FIELD_RELATED_CHUNKS: '[{"target_chunk_id": "other_chunk", "type": "semantic", "score": 0.9}]',
            FIELD_DEDUP_SOURCES: '[{"original_document": "merged_doc"}]',
        }

        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': ['uuid_123'],
            'documents': ['Test content for the chunk'],
            'metadatas': [persisted_metadata]
        }

        result = chunk_manager._load_chunk_from_chromadb(chunk_id)

        assert result is True
        assert chunk_id in chunk_manager.chunk_relationships
        
        loaded = chunk_manager.chunk_relationships[chunk_id]
        assert len(loaded['related_chunks']) == 1
        assert loaded['related_chunks'][0]['target_chunk_id'] == 'other_chunk'
        assert len(loaded['deduplication_sources']) == 1
        assert loaded['deduplication_sources'][0]['original_document'] == 'merged_doc'

    def test_load_chunk_backward_compatible(self, chunk_manager, mock_memory_system):
        """Test loading old chunks without relationship fields works (backward compat)."""
        chunk_id = 'old_chunk'
        old_metadata = {
            'chunk_id': chunk_id,
            'document_id': 'old_doc',
            'chunk_index': 0,
            # No relationship fields - simulates old data
        }

        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': ['uuid_456'],
            'documents': ['Old content'],
            'metadatas': [old_metadata]
        }

        result = chunk_manager._load_chunk_from_chromadb(chunk_id)

        assert result is True
        loaded = chunk_manager.chunk_relationships[chunk_id]
        assert loaded['related_chunks'] == []  # Empty but not None
        assert loaded['deduplication_sources'] == []


class TestSystemDocumentManagement:
    """Tests for system document storage and retrieval."""

    def test_get_system_document_found(self, chunk_manager, mock_memory_system):
        """Test retrieving an existing system document."""
        doc_content = json.dumps({'merge_1': {'timestamp': 123}})
        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': ['system_doc_id'],
            'documents': [doc_content],
            'metadatas': [{'document_type': SYSTEM_DOC_TYPE_MERGE_HISTORY}]
        }

        result = chunk_manager._get_system_document(SYSTEM_DOC_TYPE_MERGE_HISTORY)

        assert result is not None
        assert result['data'] == {'merge_1': {'timestamp': 123}}
        assert result['id'] == 'system_doc_id'

    def test_get_system_document_not_found(self, chunk_manager, mock_memory_system):
        """Test retrieving non-existent system document returns None."""
        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }

        result = chunk_manager._get_system_document(SYSTEM_DOC_TYPE_MERGE_HISTORY)

        assert result is None

    def test_save_system_document_new(self, chunk_manager, mock_memory_system):
        """Test saving a new system document."""
        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }
        mock_memory_system.short_term_memory._collection.add = Mock()

        data = {'merge_1': {'timestamp': 123}}
        result = chunk_manager._save_system_document(SYSTEM_DOC_TYPE_MERGE_HISTORY, data)

        assert result is True
        mock_memory_system.short_term_memory._collection.add.assert_called_once()
        call_args = mock_memory_system.short_term_memory._collection.add.call_args
        assert 'system_merge_history' in call_args[1]['metadatas'][0]['document_type']

    def test_save_system_document_update(self, chunk_manager, mock_memory_system):
        """Test updating an existing system document."""
        # First call returns existing doc, which triggers update path
        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': ['existing_id'],
            'documents': ['{}'],
            'metadatas': [{'document_type': SYSTEM_DOC_TYPE_MERGE_HISTORY}]
        }
        mock_memory_system.short_term_memory._collection.update = Mock()

        data = {'merge_1': {'timestamp': 456}}
        result = chunk_manager._save_system_document(SYSTEM_DOC_TYPE_MERGE_HISTORY, data)

        assert result is True
        mock_memory_system.short_term_memory._collection.update.assert_called_once()


class TestMergeHistoryPersistence:
    """Tests for merge history loading and saving."""

    def test_load_merge_history_from_storage(self, chunk_manager, mock_memory_system):
        """Test loading merge history on startup."""
        merge_data = {
            'merge_1': {'timestamp': 100, 'primary_document': 'doc_1'},
            'merge_2': {'timestamp': 200, 'primary_document': 'doc_2'}
        }
        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': ['system_id'],
            'documents': [json.dumps(merge_data)],
            'metadatas': [{'document_type': SYSTEM_DOC_TYPE_MERGE_HISTORY}]
        }

        chunk_manager._load_merge_history_from_storage()

        assert chunk_manager._merge_history_loaded is True
        assert len(chunk_manager.merge_history) == 2
        assert 'merge_1' in chunk_manager.merge_history
        assert 'merge_2' in chunk_manager.merge_history

    def test_load_merge_history_empty(self, chunk_manager, mock_memory_system):
        """Test loading merge history when none exists."""
        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }

        chunk_manager._load_merge_history_from_storage()

        assert chunk_manager._merge_history_loaded is True
        assert chunk_manager.merge_history == {}

    def test_load_merge_history_idempotent(self, chunk_manager, mock_memory_system):
        """Test that loading merge history only happens once."""
        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }

        chunk_manager._load_merge_history_from_storage()
        chunk_manager._load_merge_history_from_storage()  # Second call

        # Should only query once
        assert mock_memory_system.short_term_memory._collection.get.call_count == 1

    def test_save_merge_history_prunes_old_entries(self, chunk_manager, mock_memory_system):
        """Test that saving prunes entries when over limit."""
        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }
        mock_memory_system.short_term_memory._collection.add = Mock()

        # Add more entries than the limit
        for i in range(MAX_MERGE_HISTORY_SIZE + 100):
            chunk_manager.merge_history[f'merge_{i}'] = {'timestamp': i}

        result = chunk_manager._save_merge_history_to_storage()

        assert result is True
        assert len(chunk_manager.merge_history) == MAX_MERGE_HISTORY_SIZE


class TestPersistChunkRelationships:
    """Tests for persisting chunk relationships to ChromaDB."""

    @pytest.mark.asyncio
    async def test_persist_chunk_relationships_success(self, chunk_manager, mock_memory_system):
        """Test successfully persisting chunk relationships."""
        chunk_id = 'chunk_to_persist'
        chunk_manager.chunk_relationships[chunk_id] = {
            'related_chunks': [{'target_chunk_id': 'other_chunk', 'type': 'semantic'}],
            'deduplication_sources': [],
            'relationship_strength': {}
        }

        result = await chunk_manager._persist_chunk_relationships(chunk_id)

        assert result is True
        mock_memory_system.update_document_metadata.assert_called_once()
        call_args = mock_memory_system.update_document_metadata.call_args
        assert call_args[0][0] == chunk_id
        assert FIELD_RELATED_CHUNKS in call_args[0][1]

    @pytest.mark.asyncio
    async def test_persist_chunk_relationships_nothing_to_persist(self, chunk_manager):
        """Test persisting chunk with no relationships returns True."""
        chunk_id = 'empty_chunk'
        chunk_manager.chunk_relationships[chunk_id] = {
            'related_chunks': [],
            'deduplication_sources': [],
            'relationship_strength': {}
        }

        result = await chunk_manager._persist_chunk_relationships(chunk_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_persist_chunk_relationships_not_found(self, chunk_manager):
        """Test persisting non-existent chunk returns True (nothing to do)."""
        result = await chunk_manager._persist_chunk_relationships('nonexistent')
        assert result is True


class TestRoundTrip:
    """Integration tests for serialize -> store -> load -> verify round trips."""

    def test_round_trip_chunk_relationships(self, chunk_manager, mock_memory_system):
        """Test full round trip: serialize, store, load, verify."""
        chunk_id = 'round_trip_chunk'
        original_data = {
            'chunk_id': chunk_id,
            'document_id': 'doc_rt',
            'chunk_index': 0,
            'related_chunks': [
                {'target_chunk_id': 'chunk_a', 'type': 'semantic', 'score': 0.85},
                {'target_chunk_id': 'chunk_b', 'type': 'co_occurrence', 'score': 0.7}
            ],
            'deduplication_sources': [
                {'original_document': 'merged_doc', 'merge_timestamp': 1234567890}
            ],
            'relationship_strength': {'chunk_a': 0.9, 'chunk_b': 0.7}
        }

        # Store in manager
        chunk_manager.chunk_relationships[chunk_id] = original_data

        # Serialize
        serialized = chunk_manager._serialize_chunk_relationships(chunk_id)

        # Simulate what ChromaDB would store
        stored_metadata = {
            'chunk_id': chunk_id,
            'document_id': 'doc_rt',
            'chunk_index': 0,
            **serialized
        }

        # Clear cache to simulate restart
        chunk_manager.chunk_relationships.clear()

        # Setup mock to return stored data
        mock_memory_system.short_term_memory._collection.get.return_value = {
            'ids': ['uuid'],
            'documents': ['content'],
            'metadatas': [stored_metadata]
        }

        # Load from "ChromaDB"
        chunk_manager._load_chunk_from_chromadb(chunk_id)

        # Verify
        loaded = chunk_manager.chunk_relationships[chunk_id]
        assert len(loaded['related_chunks']) == 2
        assert loaded['related_chunks'][0]['target_chunk_id'] == 'chunk_a'
        assert loaded['related_chunks'][1]['type'] == 'co_occurrence'
        assert len(loaded['deduplication_sources']) == 1
        assert loaded['relationship_strength']['chunk_a'] == 0.9
