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

    @pytest.mark.asyncio
    async def test_delete_document_success_long_term(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test successful deletion of a document from long-term memory."""
        document_id = "doc_456"
        # Short-term has no matching documents
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['other_chunk'],
            'documents': ['other content'],
            'metadatas': [{'document_id': 'other_doc'}]
        }
        # Long-term has the document
        mock_long_term_memory._collection.get.return_value = {
            'ids': ['lt_chunk_1', 'lt_chunk_2'],
            'documents': ['lt_content1', 'lt_content2'],
            'metadatas': [
                {'document_id': document_id, 'chunk_index': 0},
                {'document_id': document_id, 'chunk_index': 1}
            ]
        }

        result = await update_service.delete_document(document_id)

        assert result['success'] is True
        assert result['chunks_deleted'] == 2
        assert result['collection'] == 'long_term'

    @pytest.mark.asyncio
    async def test_delete_document_with_memory_id(
            self, update_service, mock_short_term_memory):
        """Test deletion using memory_id instead of document_id in metadata."""
        memory_id = "mem_789"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [{'memory_id': memory_id, 'chunk_index': 0}]
        }

        result = await update_service.delete_document(memory_id)

        assert result['success'] is True
        assert result['chunks_deleted'] == 1

    @pytest.mark.asyncio
    async def test_delete_document_not_found(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test deletion when document is not found in any collection."""
        document_id = "nonexistent_doc"
        mock_short_term_memory._collection.get.return_value = {
            'ids': [],
            'documents': [],
            'metadatas': []
        }
        mock_long_term_memory._collection.get.return_value = {
            'ids': [],
            'documents': [],
            'metadatas': []
        }

        result = await update_service.delete_document(document_id)

        assert result['success'] is False
        assert result['chunks_deleted'] == 0
        assert result['collection'] is None
        assert "not found" in result['message']

    @pytest.mark.asyncio
    async def test_delete_document_cleans_up_chunk_relationships(
        self,
        update_service,
        mock_short_term_memory,
        mock_chunk_manager
    ):
        """Test that chunk relationships are cleaned up on deletion."""
        document_id = "doc_with_relations"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1', 'chunk_2'],
            'documents': ['content1', 'content2'],
            'metadatas': [
                {'document_id': document_id, 'chunk_index': 0},
                {'document_id': document_id, 'chunk_index': 1}
            ]
        }
        mock_chunk_manager.document_relationships = {
            document_id: {'chunks': ['chunk_1', 'chunk_2']}}
        mock_chunk_manager.chunk_relationships = {
            'chunk_1': {'related': []},
            'chunk_2': {'related': []}
        }

        result = await update_service.delete_document(document_id)

        assert result['success'] is True
        assert document_id not in mock_chunk_manager.document_relationships
        assert 'chunk_1' not in mock_chunk_manager.chunk_relationships
        assert 'chunk_2' not in mock_chunk_manager.chunk_relationships

    @pytest.mark.asyncio
    async def test_delete_document_handles_relationship_cleanup_error(
        self,
        update_service,
        mock_short_term_memory,
        mock_chunk_manager
    ):
        """Test that errors in relationship cleanup don't fail the deletion."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [{'document_id': document_id}]
        }
        # Make document_relationships raise an error
        mock_chunk_manager.document_relationships = MagicMock()
        mock_chunk_manager.document_relationships.__contains__ = Mock(
            side_effect=Exception("Cleanup error"))

        result = await update_service.delete_document(document_id)

        # Deletion should still succeed
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_delete_document_collection_error(
            self, update_service, mock_short_term_memory):
        """Test handling of collection errors during deletion."""
        document_id = "doc_error"
        mock_short_term_memory._collection.get.side_effect = Exception(
            "Database error")

        result = await update_service.delete_document(document_id)

        # Should continue to next collection and eventually return not found
        assert result['success'] is False
        assert "not found" in result['message']

    @pytest.mark.asyncio
    async def test_delete_document_with_none_metadata(
            self, update_service, mock_short_term_memory):
        """Test deletion handles None metadata entries gracefully."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1', 'chunk_2', 'chunk_3'],
            'documents': ['content1', 'content2', 'content3'],
            'metadatas': [
                None,
                {'document_id': document_id},
                {'document_id': 'other_doc'}
            ]
        }

        result = await update_service.delete_document(document_id)

        assert result['success'] is True
        assert result['chunks_deleted'] == 1

    @pytest.mark.asyncio
    async def test_delete_document_collection_without_internal_collection(
        self,
        mock_long_term_memory,
        mock_chunk_manager
    ):
        """Test deletion when collection doesn't have _collection attribute."""
        mock_no_collection = Mock(spec=[])  # Mock without _collection
        service = DocumentUpdateService(
            short_term_memory=mock_no_collection,
            long_term_memory=mock_long_term_memory,
            chunk_manager=mock_chunk_manager
        )
        mock_long_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }

        result = await service.delete_document("doc_123")

        assert result['success'] is False


class TestUpdateDocumentImportance:
    """Tests for update_document_importance method."""

    @pytest.mark.asyncio
    async def test_update_importance_success(
        self,
        update_service,
        mock_short_term_memory,
        mock_lifecycle_manager
    ):
        """Test successful importance score update."""
        document_id = "doc_123"
        new_importance = 0.75
        old_importance = 0.5
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1', 'chunk_2'],
            'documents': ['content1', 'content2'],
            'metadatas': [
                {'document_id': document_id,
                 'importance_score': old_importance,
                 'ttl_tier': 'medium_frequency'},
                {'document_id': document_id,
                 'importance_score': old_importance,
                 'ttl_tier': 'medium_frequency'}
            ]
        }

        result = await update_service.update_document_importance(document_id, new_importance)

        assert result['success'] is True
        assert result['old_importance'] == old_importance
        assert result['new_importance'] == new_importance
        assert result['chunks_updated'] == 2
        assert result['collection'] == 'short_term'
        mock_short_term_memory._collection.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_importance_with_reason(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test importance update with a reason provided."""
        document_id = "doc_123"
        new_importance = 0.3
        reason = "User indicated document is less relevant"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [{'document_id': document_id, 'importance_score': 0.7}]
        }

        result = await update_service.update_document_importance(
            document_id, new_importance, reason=reason
        )

        assert result['success'] is True
        # Verify that the reason was included in the update
        call_args = mock_short_term_memory._collection.update.call_args
        updated_metadata = call_args[1]['metadatas'][0]
        assert updated_metadata['importance_change_reason'] == reason

    @pytest.mark.asyncio
    async def test_update_importance_recalculates_ttl(
        self,
        update_service,
        mock_short_term_memory,
        mock_lifecycle_manager
    ):
        """Test that TTL is recalculated when importance changes."""
        document_id = "doc_123"
        new_importance = 0.8
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [
                {'document_id': document_id,
                 'importance_score': 0.3,
                 'ttl_tier': 'high_frequency'}
            ]
        }

        result = await update_service.update_document_importance(document_id, new_importance)

        assert result['success'] is True
        mock_lifecycle_manager.ttl_manager.add_ttl_metadata.assert_called()

    @pytest.mark.asyncio
    async def test_update_importance_invalid_score_negative(
            self, update_service):
        """Test that negative importance scores are rejected."""
        result = await update_service.update_document_importance("doc_123", -0.1)

        assert result['success'] is False
        assert "between 0.0 and 1.0" in result['message']

    @pytest.mark.asyncio
    async def test_update_importance_invalid_score_above_one(
            self, update_service):
        """Test that importance scores above 1.0 are rejected."""
        result = await update_service.update_document_importance("doc_123", 1.5)

        assert result['success'] is False
        assert "between 0.0 and 1.0" in result['message']

    @pytest.mark.asyncio
    async def test_update_importance_boundary_zero(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test importance update with boundary value 0.0."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [{'document_id': document_id, 'importance_score': 0.5}]
        }

        result = await update_service.update_document_importance(document_id, 0.0)

        assert result['success'] is True
        assert result['new_importance'] == 0.0

    @pytest.mark.asyncio
    async def test_update_importance_boundary_one(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test importance update with boundary value 1.0."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [{'document_id': document_id, 'importance_score': 0.5}]
        }

        result = await update_service.update_document_importance(document_id, 1.0)

        assert result['success'] is True
        assert result['new_importance'] == 1.0

    @pytest.mark.asyncio
    async def test_update_importance_document_not_found(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test importance update when document is not found."""
        mock_short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }
        mock_long_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }

        result = await update_service.update_document_importance("nonexistent", 0.5)

        assert result['success'] is False
        assert "not found" in result['message']

    @pytest.mark.asyncio
    async def test_update_importance_in_long_term(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test importance update for document in long-term memory."""
        document_id = "lt_doc_456"
        mock_short_term_memory._collection.get.return_value = {
            'ids': [], 'documents': [], 'metadatas': []
        }
        mock_long_term_memory._collection.get.return_value = {
            'ids': ['lt_chunk_1'],
            'documents': ['content'],
            'metadatas': [{'document_id': document_id, 'importance_score': 0.6}]
        }

        result = await update_service.update_document_importance(document_id, 0.9)

        assert result['success'] is True
        assert result['collection'] == 'long_term'

    @pytest.mark.asyncio
    async def test_update_importance_without_lifecycle_manager(
        self,
        update_service_minimal,
        mock_short_term_memory
    ):
        """Test importance update without lifecycle manager (no TTL recalculation)."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [{'document_id': document_id, 'importance_score': 0.5}]
        }

        result = await update_service_minimal.update_document_importance(document_id, 0.8)

        assert result['success'] is True
        # TTL tier should remain unchanged since no lifecycle manager
        call_args = mock_short_term_memory._collection.update.call_args
        updated_metadata = call_args[1]['metadatas'][0]
        assert 'importance_changed_at' in updated_metadata

    @pytest.mark.asyncio
    async def test_update_importance_uses_memory_id_fallback(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test importance update using memory_id when document_id is not present."""
        memory_id = "mem_789"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [{'memory_id': memory_id, 'importance_score': 0.4}]
        }

        result = await update_service.update_document_importance(memory_id, 0.7)

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_update_importance_handles_collection_error(
        self,
        update_service,
        mock_short_term_memory,
        mock_long_term_memory
    ):
        """Test importance update handles collection errors gracefully."""
        document_id = "doc_error"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [{'document_id': document_id, 'importance_score': 0.5}]
        }
        mock_short_term_memory._collection.update.side_effect = Exception(
            "Update failed")

        result = await update_service.update_document_importance(document_id, 0.8)

        assert result['success'] is False
        assert "Error updating document" in result['message']

    @pytest.mark.asyncio
    async def test_update_importance_preserves_existing_metadata(
        self,
        update_service,
        mock_short_term_memory
    ):
        """Test that importance update preserves existing metadata fields."""
        document_id = "doc_123"
        original_metadata = {
            'document_id': document_id,
            'importance_score': 0.5,
            'source': 'user_input',
            'tags': ['important', 'work'],
            'created_at': 1234567890
        }
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['content'],
            'metadatas': [original_metadata]
        }

        result = await update_service.update_document_importance(document_id, 0.8)

        assert result['success'] is True
        call_args = mock_short_term_memory._collection.update.call_args
        updated_metadata = call_args[1]['metadatas'][0]
        assert updated_metadata['source'] == 'user_input'
        assert updated_metadata['tags'] == ['important', 'work']
        assert updated_metadata['created_at'] == 1234567890


class TestUpdateDocumentContent:
    """Tests for update_document_content method."""

    @pytest.mark.asyncio
    async def test_update_content_success(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test successful content update."""
        document_id = "doc_123"
        new_content = "Updated document content"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1', 'chunk_2'],
            'documents': ['old content 1', 'old content 2'],
            'metadatas': [
                {'document_id': document_id, 'importance_score': 0.7},
                {'document_id': document_id, 'importance_score': 0.7}
            ]
        }

        result = await update_service.update_document_content(document_id, new_content)

        assert result['success'] is True
        assert result['old_chunks'] == 2
        assert result['new_chunks'] == 2
        mock_storage_service.add_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_content_preserves_importance(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test that importance score is preserved when preserve_importance=True."""
        document_id = "doc_123"
        original_importance = 0.85
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id, 'importance_score': original_importance}]
        }

        result = await update_service.update_document_content(
            document_id, "new content", preserve_importance=True
        )

        assert result['success'] is True
        assert result['importance_preserved'] is True
        call_args = mock_storage_service.add_memory.call_args
        assert call_args[1]['context']['preserved_importance'] == original_importance

    @pytest.mark.asyncio
    async def test_update_content_does_not_preserve_importance(
        self,
        update_service,
        mock_short_term_memory,
        mock_storage_service
    ):
        """Test that importance score is not preserved when preserve_importance=False."""
        document_id = "doc_123"
        mock_short_term_memory._collection.get.return_value = {
            'ids': ['chunk_1'],
            'documents': ['old content'],
            'metadatas': [{'document_id': document_id, 'importance_score': 0.9}]
        }

        result = await update_service.update_document_content(
            document_id, "new content", preserve_importance=False
        )

        assert result['success'] is True
        assert result['importance_preserved'] is False

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
