"""
Unit tests for DocumentUpdateService

Tests all public methods:
- delete_document
- update_document_importance
- update_document_content
- set_lifecycle_manager
- set_storage_service
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, MagicMock


from src.mcp_memory_server.memory.services.update import DocumentUpdateService


# Fixtures for mocking dependencies


@pytest.fixture
def mock_short_term_memory():
    """Create a mock Chroma collection for short-term memory."""
    mock = Mock()
    mock._collection = Mock()
    mock._collection.get = Mock(return_value={
        'ids': [],
        'documents': [],
        'metadatas': []
    })
    mock._collection.delete = Mock()
    mock._collection.update = Mock()
    return mock


@pytest.fixture
def mock_long_term_memory():
    """Create a mock Chroma collection for long-term memory."""
    mock = Mock()
    mock._collection = Mock()
    mock._collection.get = Mock(return_value={
        'ids': [],
        'documents': [],
        'metadatas': []
    })
    mock._collection.delete = Mock()
    mock._collection.update = Mock()
    return mock


@pytest.fixture
def mock_chunk_manager():
    """Create a mock ChunkRelationshipManager."""
    mock = Mock()
    mock.document_relationships = {}
    mock.chunk_relationships = {}
    return mock


@pytest.fixture
def mock_lifecycle_manager():
    """Create a mock LifecycleManager with TTL manager."""
    mock = Mock()
    mock.ttl_manager = Mock()
    mock.ttl_manager.add_ttl_metadata = Mock(side_effect=lambda meta, imp: {
        **meta,
        'ttl_tier': 'medium_frequency' if imp < 0.7 else 'static',
        'ttl_seconds': 3600 if imp < 0.7 else 604800,
        'ttl_expiry': time.time() + (3600 if imp < 0.7 else 604800)
    })
    return mock


@pytest.fixture
def mock_storage_service():
    """Create a mock MemoryStorageService."""
    mock = Mock()
    mock.add_memory = AsyncMock(return_value={
        'success': True,
        'memory_id': 'new_mem_123',
        'chunks_added': 2,
        'collection': 'short_term'
    })
    return mock


@pytest.fixture
def update_service(
    mock_short_term_memory,
    mock_long_term_memory,
    mock_chunk_manager,
    mock_lifecycle_manager,
    mock_storage_service
):
    """Create a DocumentUpdateService with all mocked dependencies."""
    service = DocumentUpdateService(
        short_term_memory=mock_short_term_memory,
        long_term_memory=mock_long_term_memory,
        chunk_manager=mock_chunk_manager,
        lifecycle_manager=mock_lifecycle_manager,
        storage_service=mock_storage_service
    )
    return service


@pytest.fixture
def update_service_minimal(mock_short_term_memory,
                           mock_long_term_memory, mock_chunk_manager):
    """Create a DocumentUpdateService with minimal dependencies (no lifecycle/storage)."""
    return DocumentUpdateService(
        short_term_memory=mock_short_term_memory,
        long_term_memory=mock_long_term_memory,
        chunk_manager=mock_chunk_manager,
        lifecycle_manager=None,
        storage_service=None
    )


class TestDocumentUpdateServiceInit:
    """Tests for DocumentUpdateService initialization."""

    def test_init_with_all_dependencies(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_chunk_manager,
        mock_lifecycle_manager,
        mock_storage_service
    ):
        """Test initialization with all dependencies provided."""
        service = DocumentUpdateService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            chunk_manager=mock_chunk_manager,
            lifecycle_manager=mock_lifecycle_manager,
            storage_service=mock_storage_service
        )

        assert service.short_term_memory is mock_short_term_memory
        assert service.long_term_memory is mock_long_term_memory
        assert service.chunk_manager is mock_chunk_manager
        assert service.lifecycle_manager is mock_lifecycle_manager
        assert service.storage_service is mock_storage_service

    def test_init_with_optional_dependencies_none(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_chunk_manager
    ):
        """Test initialization with optional dependencies set to None."""
        service = DocumentUpdateService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            chunk_manager=mock_chunk_manager
        )

        assert service.lifecycle_manager is None
        assert service.storage_service is None


class TestSetLifecycleManager:
    """Tests for set_lifecycle_manager method."""

    def test_set_lifecycle_manager(
            self, update_service_minimal, mock_lifecycle_manager):
        """Test setting lifecycle manager after initialization."""
        assert update_service_minimal.lifecycle_manager is None

        update_service_minimal.set_lifecycle_manager(mock_lifecycle_manager)

        assert update_service_minimal.lifecycle_manager is mock_lifecycle_manager

    def test_set_lifecycle_manager_overwrites_existing(
            self, update_service, mock_lifecycle_manager):
        """Test that setting lifecycle manager overwrites existing one."""
        new_lifecycle_manager = Mock()

        update_service.set_lifecycle_manager(new_lifecycle_manager)

        assert update_service.lifecycle_manager is new_lifecycle_manager


class TestSetStorageService:
    """Tests for set_storage_service method."""

    def test_set_storage_service(
            self, update_service_minimal, mock_storage_service):
        """Test setting storage service after initialization."""
        assert update_service_minimal.storage_service is None

        update_service_minimal.set_storage_service(mock_storage_service)

        assert update_service_minimal.storage_service is mock_storage_service

    def test_set_storage_service_overwrites_existing(
            self, update_service, mock_storage_service):
        """Test that setting storage service overwrites existing one."""
        new_storage_service = Mock()

        update_service.set_storage_service(new_storage_service)

        assert update_service.storage_service is new_storage_service


class TestGetCollection:
    """Tests for _get_collection private method."""

    def test_get_collection_short_term(
            self, update_service, mock_short_term_memory):
        """Test getting short_term collection."""
        result = update_service._get_collection("short_term")
        assert result is mock_short_term_memory

    def test_get_collection_long_term(
            self, update_service, mock_long_term_memory):
        """Test getting long_term collection."""
        result = update_service._get_collection("long_term")
        assert result is mock_long_term_memory

    def test_get_collection_invalid_name(self, update_service):
        """Test getting collection with invalid name returns None."""
        result = update_service._get_collection("invalid_collection")
        assert result is None

    def test_get_collection_empty_string(self, update_service):
        """Test getting collection with empty string returns None."""
        result = update_service._get_collection("")
        assert result is None


class TestDeleteDocument:
    """Tests for delete_document method."""

    @pytest.mark.asyncio
    async def test_delete_document_success_short_term(
        self,
        update_service,
        mock_short_term_memory,
        mock_chunk_manager
    ):
        """Test successful deletion of a document from short-term memory."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1', 'chunk_2', 'chunk_3'],
            'documents': ['content1', 'content2', 'content3'],
            'metadatas': [
                {'document_id': document_id, 'chunk_index': 0},
                {'document_id': document_id, 'chunk_index': 1},
                {'document_id': document_id, 'chunk_index': 2}
            ]
        }

        result = await update_service.delete_document(document_id)

        assert result['success'] is True
        assert result['document_id'] == document_id
        assert result['chunks_deleted'] == 3
        assert result['collection'] == 'short_term'
        mock_short_term_memory._collection.delete.assert_called_once_with(
            ids=['chunk_1', 'chunk_2', 'chunk_3']
        )


class TestUpdateDocumentMetadata:
    """Tests for update_document_metadata method."""

    @pytest.mark.asyncio
    async def test_update_metadata_success(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test successful metadata update on a chunk."""
        chunk_id = "doc_123_chunk_0"
        metadata_updates = {
            'related_chunks_data': '[{"target": "doc_456_chunk_0"}]',
            'custom_field': 'custom_value'
        }
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chromadb_uuid_123'],
            'documents': ['content'],
            'metadatas': [{'chunk_id': chunk_id, 'existing_field': 'keep_this'}]
        }

        result = await update_service.update_document_metadata(chunk_id, metadata_updates)

        assert result['success'] is True
        assert result['chunk_id'] == chunk_id
        assert 'related_chunks_data' in result['fields_updated']
        assert 'custom_field' in result['fields_updated']
        assert result['collection'] == 'short_term'

        # Verify ChromaDB update was called with merged metadata
        mock_short_term_memory._collection.update.assert_called_once()
        call_args = mock_short_term_memory._collection.update.call_args
        updated_metadata = call_args[1]['metadatas'][0]
        assert updated_metadata['existing_field'] == 'keep_this'
        assert updated_metadata['related_chunks_data'] == '[{"target": "doc_456_chunk_0"}]'
        assert updated_metadata['custom_field'] == 'custom_value'
        assert 'metadata_updated_at' in updated_metadata

    @pytest.mark.asyncio
    async def test_update_metadata_in_long_term(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test metadata update for chunk in long-term memory."""
        chunk_id = "lt_doc_chunk_0"
        mock_short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }
        mock_long_term_memory._collection.get.return_value = {
            'ids': ['lt_uuid_456'],
            'documents': ['content'],
            'metadatas': [{'chunk_id': chunk_id}]
        }

        result = await update_service.update_document_metadata(
            chunk_id, {'new_field': 'value'}
        )

        assert result['success'] is True
        assert result['collection'] == 'long_term'
        mock_long_term_memory._collection.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_metadata_chunk_not_found(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test metadata update when chunk is not found."""
        mock_short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }
        mock_long_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }

        result = await update_service.update_document_metadata(
            'nonexistent_chunk', {'field': 'value'}
        )

        assert result['success'] is False
        assert 'not found' in result['message']

    @pytest.mark.asyncio
    async def test_update_metadata_empty_chunk_id_rejected(self, update_service):
        """Test that empty chunk_id is rejected."""
        result = await update_service.update_document_metadata('', {'field': 'value'})

        assert result['success'] is False
        assert 'chunk_id' in result['message']

    @pytest.mark.asyncio
    async def test_update_metadata_none_chunk_id_rejected(self, update_service):
        """Test that None chunk_id is rejected."""
        result = await update_service.update_document_metadata(None, {'field': 'value'})

        assert result['success'] is False
        assert 'chunk_id' in result['message']

    @pytest.mark.asyncio
    async def test_update_metadata_empty_updates_rejected(self, update_service):
        """Test that empty metadata_updates is rejected."""
        result = await update_service.update_document_metadata('chunk_123', {})

        assert result['success'] is False
        assert 'metadata_updates' in result['message']

    @pytest.mark.asyncio
    async def test_update_metadata_none_updates_rejected(self, update_service):
        """Test that None metadata_updates is rejected."""
        result = await update_service.update_document_metadata('chunk_123', None)

        assert result['success'] is False
        assert 'metadata_updates' in result['message']

    @pytest.mark.asyncio
    async def test_update_metadata_handles_collection_error(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test metadata update handles collection errors gracefully."""
        chunk_id = "chunk_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['uuid_123'],
            'documents': ['content'],
            'metadatas': [{'chunk_id': chunk_id}]
        }
        mock_short_term_memory._collection.update.side_effect = Exception("Update failed")

        result = await update_service.update_document_metadata(
            chunk_id, {'field': 'value'}
        )

        assert result['success'] is False
        assert 'Error updating metadata' in result['message']

    @pytest.mark.asyncio
    async def test_update_metadata_preserves_all_existing_fields(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test that all existing metadata fields are preserved."""
        chunk_id = "chunk_123"
        existing_metadata = {
            'chunk_id': chunk_id,
            'document_id': 'doc_123',
            'chunk_index': 0,
            'importance_score': 0.75,
            'timestamp': 1234567890,
            'previous_chunk': None,
            'next_chunk': 'chunk_456'
        }
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['uuid_123'],
            'documents': ['content'],
            'metadatas': [existing_metadata]
        }

        result = await update_service.update_document_metadata(
            chunk_id, {'new_relationship_field': 'some_data'}
        )

        assert result['success'] is True
        call_args = mock_short_term_memory._collection.update.call_args
        updated_metadata = call_args[1]['metadatas'][0]

        # All existing fields should be preserved
        assert updated_metadata['chunk_id'] == chunk_id
        assert updated_metadata['document_id'] == 'doc_123'
        assert updated_metadata['chunk_index'] == 0
        assert updated_metadata['importance_score'] == 0.75
        assert updated_metadata['timestamp'] == 1234567890
        assert updated_metadata['previous_chunk'] is None
        assert updated_metadata['next_chunk'] == 'chunk_456'
        # New field should be added
        assert updated_metadata['new_relationship_field'] == 'some_data'

    @pytest.mark.asyncio
    async def test_update_metadata_overwrites_existing_field(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test that existing fields can be overwritten."""
        chunk_id = "chunk_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['uuid_123'],
            'documents': ['content'],
            'metadatas': [{'chunk_id': chunk_id, 'related_chunks_data': '[]'}]
        }

        result = await update_service.update_document_metadata(
            chunk_id, {'related_chunks_data': '[{"target": "new_chunk"}]'}
        )

        assert result['success'] is True
        call_args = mock_short_term_memory._collection.update.call_args
        updated_metadata = call_args[1]['metadatas'][0]
        assert updated_metadata['related_chunks_data'] == '[{"target": "new_chunk"}]'

    @pytest.mark.asyncio
    async def test_update_metadata_with_json_serialized_data(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test updating metadata with JSON-serialized relationship data."""
        import json
        chunk_id = "chunk_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['uuid_123'],
            'documents': ['content'],
            'metadatas': [{'chunk_id': chunk_id}]
        }

        relationship_data = [
            {'target_chunk_id': 'chunk_456', 'type': 'semantic', 'score': 0.85},
            {'target_chunk_id': 'chunk_789', 'type': 'co_occurrence', 'score': 0.7}
        ]
        dedup_data = [
            {'original_document': 'old_doc', 'merge_timestamp': 1234567890}
        ]

        result = await update_service.update_document_metadata(
            chunk_id,
            {
                'related_chunks_data': json.dumps(relationship_data),
                'dedup_sources_data': json.dumps(dedup_data)
            }
        )

        assert result['success'] is True
        assert len(result['fields_updated']) == 2

        call_args = mock_short_term_memory._collection.update.call_args
        updated_metadata = call_args[1]['metadatas'][0]

        # Verify the JSON data was stored correctly
        stored_relationships = json.loads(updated_metadata['related_chunks_data'])
        assert len(stored_relationships) == 2
        assert stored_relationships[0]['target_chunk_id'] == 'chunk_456'


    @pytest.mark.asyncio
    async def test_update_content_with_new_metadata(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test content update with new metadata provided."""
        document_id = "doc_123"
        new_metadata = {'tags': ['updated', 'modified'], 'source': 'api'}
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id, 'tags': ['original']}]
        }

        result = await update_service.update_document_content(
            document_id, "new content", new_metadata=new_metadata
        )

        assert result['success'] is True
        call_args = mock_storage_service.add_memory.call_args
        metadata = call_args[1]['metadata']
        assert metadata['tags'] == ['updated', 'modified']
        assert metadata['source'] == 'api'

    @pytest.mark.asyncio
    async def test_update_content_empty_content_rejected(self, update_service):
        """Test that empty content is rejected."""
        result = await update_service.update_document_content("doc_123", "")

        assert result['success'] is False
        assert "non-empty string" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_none_content_rejected(self, update_service):
        """Test that None content is rejected."""
        result = await update_service.update_document_content("doc_123", None)

        assert result['success'] is False
        assert "non-empty string" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_non_string_content_rejected(
            self, update_service):
        """Test that non-string content is rejected."""
        result = await update_service.update_document_content("doc_123", 12345)

        assert result['success'] is False
        assert "non-empty string" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_empty_document_id_rejected(
            self, update_service):
        """Test that empty document_id is rejected."""
        result = await update_service.update_document_content("", "new content")

        assert result['success'] is False
        assert "Document ID" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_none_document_id_rejected(
            self, update_service):
        """Test that None document_id is rejected."""
        result = await update_service.update_document_content(None, "new content")

        assert result['success'] is False
        assert "Document ID" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_no_storage_service(
            self, update_service_minimal):
        """Test content update fails without storage service."""
        result = await update_service_minimal.update_document_content("doc_123", "new content")

        assert result['success'] is False
        assert "Storage service not configured" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_document_not_found(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test content update when document is not found."""
        mock_short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }
        mock_long_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }

        result = await update_service.update_document_content("nonexistent", "new content")

        assert result['success'] is False
        assert "not found" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_increments_update_count(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test that update_count is incremented."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id, 'update_count': 2}]
        }

        result = await update_service.update_document_content(document_id, "new content")

        assert result['success'] is True
        call_args = mock_storage_service.add_memory.call_args
        metadata = call_args[1]['metadata']
        assert metadata['update_count'] == 3

    @pytest.mark.asyncio
    async def test_update_content_sets_updated_at(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test that updated_at timestamp is set."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id}]
        }

        before_time = time.time()
        result = await update_service.update_document_content(document_id, "new content")
        after_time = time.time()

        assert result['success'] is True
        call_args = mock_storage_service.add_memory.call_args
        metadata = call_args[1]['metadata']
        assert before_time <= metadata['updated_at'] <= after_time

    @pytest.mark.asyncio
    async def test_update_content_add_memory_fails(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test content update when add_memory fails."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id}]
        }
        mock_storage_service.add_memory.return_value = {
            'success': False,
            'message': 'Storage error'
        }

        result = await update_service.update_document_content(document_id, "new content")

        assert result['success'] is False
        assert "Failed to add" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_add_memory_exception(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test content update handles add_memory exception."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id}]
        }
        mock_storage_service.add_memory.side_effect = Exception(
            "Storage exception")

        result = await update_service.update_document_content(document_id, "new content")

        assert result['success'] is False
        assert "Error adding" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_from_long_term(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_storage_service
    ):
        """Test content update for document in long-term memory."""
        document_id = "lt_doc_456"
        mock_short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }
        mock_long_term_memory._collection.get.return_value = {
            'ids': ['lt_chunk_1'],
            'documents': ['old long-term content'],
            'metadatas': [{'document_id': document_id, 'importance_score': 0.9}]
        }

        result = await update_service.update_document_content(document_id, "new content")

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_update_content_delete_fails(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test content update when delete fails."""
        document_id = "doc_123"
        # First call returns the document, second call (after delete attempt)
        # returns nothing
        mock_short_term_memory._collection.get.side_effect = [
            {
                'ids': ['chunk_1'],
                'documents': ['old content'],
                'metadatas': [{'document_id': document_id}]
            },
            {
                'ids': [],
                'documents': [],
                'metadatas': []
            }
        ]
        mock_short_term_memory._collection.delete.side_effect = Exception(
            "Delete failed")

        result = await update_service.update_document_content(document_id, "new content")

        # Should fail since delete failed
        assert result['success'] is False

    @pytest.mark.asyncio
    async def test_update_content_returns_new_document_id(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test that new document ID is returned in result."""
        document_id = "doc_123"
        new_document_id = "new_doc_456"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id}]
        }
        mock_storage_service.add_memory.return_value = {
            'success': True,
            'memory_id': new_document_id,
            'chunks_added': 1
        }

        result = await update_service.update_document_content(document_id, "new content")

        assert result['success'] is True
        assert result['new_document_id'] == new_document_id

    @pytest.mark.asyncio
    async def test_update_content_handles_search_exception(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test content update handles search exception gracefully."""
        mock_short_term_memory._collection.get.side_effect = Exception(
            "Search error")
        mock_long_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }

        result = await update_service.update_document_content("doc_123", "new content")

        # Should report not found since search failed
        assert result['success'] is False
        assert "not found" in result['message']

    @pytest.mark.asyncio
    async def test_update_content_merges_existing_and_new_metadata(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test that existing metadata is merged with new metadata."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{
                'document_id': document_id,
                'original_field': 'keep_this',
                'override_field': 'old_value'
            }]
        }
        new_metadata = {'override_field': 'new_value', 'new_field': 'added'}

        result = await update_service.update_document_content(
            document_id, "new content", new_metadata=new_metadata
        )

        assert result['success'] is True
        call_args = mock_storage_service.add_memory.call_args
        metadata = call_args[1]['metadata']
        assert metadata['original_field'] == 'keep_this'
        assert metadata['override_field'] == 'new_value'
        assert metadata['new_field'] == 'added'

    @pytest.mark.asyncio
    async def test_update_content_first_update(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test content update when document has no previous update_count."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id}]  # No update_count
        }

        result = await update_service.update_document_content(document_id, "new content")

        assert result['success'] is True
        call_args = mock_storage_service.add_memory.call_args
        metadata = call_args[1]['metadata']
        assert metadata['update_count'] == 1

    @pytest.mark.asyncio
    async def test_update_content_no_importance_to_preserve(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test content update when there's no importance to preserve."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id}]  # No importance_score
        }

        result = await update_service.update_document_content(
            document_id, "new content", preserve_importance=True
        )

        assert result['success'] is True
        assert result['importance_preserved'] is False
