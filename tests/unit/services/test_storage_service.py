"""
Unit tests for MemoryStorageService

Tests cover:
- add_memory: Success cases, error handling, deduplication, collection routing
- set_lifecycle_manager: Setting lifecycle manager
- _chunk_content: Content chunking for various languages
- _filter_complex_metadata: Metadata filtering for ChromaDB compatibility
- remove_documents_from_collection: Document removal from collections
"""

import pytest
import json
import time
from unittest.mock import Mock, AsyncMock

from src.mcp_memory_server.memory.services.storage import MemoryStorageService


# Fixtures

@pytest.fixture
def mock_short_term_memory():
    """Mock Chroma collection for short-term memory."""
    mock = Mock()
    mock.add_documents = Mock()
    mock._collection = Mock()
    mock._collection.delete = Mock()
    return mock


@pytest.fixture
def mock_long_term_memory():
    """Mock Chroma collection for long-term memory."""
    mock = Mock()
    mock.add_documents = Mock()
    mock._collection = Mock()
    mock._collection.delete = Mock()
    return mock


@pytest.fixture
def mock_chunk_manager():
    """Mock ChunkRelationshipManager."""
    mock = Mock()
    mock.create_document_with_relationships = AsyncMock(return_value=[
        Mock(page_content="chunk1", metadata={'chunk_id': 'chunk_1'}),
        Mock(page_content="chunk2", metadata={'chunk_id': 'chunk_2'})
    ])
    return mock


@pytest.fixture
def mock_importance_scorer():
    """Mock MemoryImportanceScorer."""
    mock = Mock()
    mock.calculate_importance = Mock(return_value=0.8)
    return mock


@pytest.fixture
def mock_deduplicator():
    """Mock MemoryDeduplicator."""
    mock = Mock()
    mock.enabled = False
    mock.check_ingestion_duplicates = AsyncMock(
        return_value=('add_new', None, 0.0))
    mock.boost_existing_document = Mock()
    return mock


@pytest.fixture
def mock_lifecycle_manager():
    """Mock LifecycleManager."""
    mock = Mock()
    mock.process_document_lifecycle = Mock(side_effect=lambda content, metadata, importance: {
        **metadata,
        'ttl': 86400,
        'lifecycle_stage': 'active'
    })
    return mock


@pytest.fixture
def storage_service(
    mock_short_term_memory,
    mock_long_term_memory,
    mock_chunk_manager,
    mock_importance_scorer,
    mock_deduplicator
):
    """Create a MemoryStorageService instance with mocked dependencies."""
    return MemoryStorageService(
        short_term_memory=mock_short_term_memory,
        long_term_memory=mock_long_term_memory,
        chunk_manager=mock_chunk_manager,
        importance_scorer=mock_importance_scorer,
        deduplicator=mock_deduplicator,
        lifecycle_manager=None,
        config={
            'chunk_size': 1000,
            'chunk_overlap': 100,
            'short_term_threshold': 0.7,
            'long_term_threshold': 0.95
        }
    )


@pytest.fixture
def storage_service_with_lifecycle(
    mock_short_term_memory,
    mock_long_term_memory,
    mock_chunk_manager,
    mock_importance_scorer,
    mock_deduplicator,
    mock_lifecycle_manager
):
    """Create a MemoryStorageService instance with lifecycle manager."""
    return MemoryStorageService(
        short_term_memory=mock_short_term_memory,
        long_term_memory=mock_long_term_memory,
        chunk_manager=mock_chunk_manager,
        importance_scorer=mock_importance_scorer,
        deduplicator=mock_deduplicator,
        lifecycle_manager=mock_lifecycle_manager,
        config={
            'chunk_size': 1000,
            'chunk_overlap': 100,
            'short_term_threshold': 0.7,
            'long_term_threshold': 0.95
        }
    )


class TestMemoryStorageServiceInit:
    """Tests for MemoryStorageService initialization."""

    def test_init_with_default_config(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_chunk_manager,
        mock_importance_scorer,
        mock_deduplicator
    ):
        """Test initialization with default configuration."""
        service = MemoryStorageService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            chunk_manager=mock_chunk_manager,
            importance_scorer=mock_importance_scorer,
            deduplicator=mock_deduplicator
        )

        assert service.chunk_size == 1000
        assert service.chunk_overlap == 100
        assert service.short_term_threshold == 0.7
        assert service.long_term_threshold == 0.95
        assert service.lifecycle_manager is None

    def test_init_with_custom_config(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_chunk_manager,
        mock_importance_scorer,
        mock_deduplicator
    ):
        """Test initialization with custom configuration."""
        custom_config = {
            'chunk_size': 500,
            'chunk_overlap': 50,
            'short_term_threshold': 0.5,
            'long_term_threshold': 0.9
        }

        service = MemoryStorageService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            chunk_manager=mock_chunk_manager,
            importance_scorer=mock_importance_scorer,
            deduplicator=mock_deduplicator,
            config=custom_config
        )

        assert service.chunk_size == 500
        assert service.chunk_overlap == 50
        assert service.short_term_threshold == 0.5
        assert service.long_term_threshold == 0.9


class TestSetLifecycleManager:
    """Tests for set_lifecycle_manager method."""

    def test_set_lifecycle_manager(
            self, storage_service, mock_lifecycle_manager):
        """Test setting lifecycle manager."""
        assert storage_service.lifecycle_manager is None

        storage_service.set_lifecycle_manager(mock_lifecycle_manager)

        assert storage_service.lifecycle_manager is mock_lifecycle_manager

    def test_replace_lifecycle_manager(self, storage_service_with_lifecycle):
        """Test replacing existing lifecycle manager."""
        new_lifecycle_manager = Mock()
        original = storage_service_with_lifecycle.lifecycle_manager

        storage_service_with_lifecycle.set_lifecycle_manager(
            new_lifecycle_manager)

        assert storage_service_with_lifecycle.lifecycle_manager is new_lifecycle_manager
        assert storage_service_with_lifecycle.lifecycle_manager is not original


class TestAddMemory:
    """Tests for add_memory method."""

    @pytest.mark.asyncio
    async def test_add_memory_success_short_term(
            self, storage_service, mock_importance_scorer):
        """Test successfully adding memory to short-term collection."""
        mock_importance_scorer.calculate_importance.return_value = 0.8  # Between 0.7 and 0.95

        result = await storage_service.add_memory(
            content="This is test content",
            metadata={'source': 'test'},
            context={'session_id': '123'}
        )

        assert result['success'] is True
        assert result['collection'] == 'short_term'
        assert result['chunks_added'] == 2
        assert result['action'] == 'added'
        assert 'memory_id' in result
        assert result['importance_score'] == 0.8

    @pytest.mark.asyncio
    async def test_add_memory_success_long_term(
            self, storage_service, mock_importance_scorer):
        """Test successfully adding memory to long-term collection."""
        mock_importance_scorer.calculate_importance.return_value = 0.98  # Above 0.95

        result = await storage_service.add_memory(
            content="Critical system configuration",
            metadata={'type': 'config'}
        )

        assert result['success'] is True
        assert result['collection'] == 'long_term'
        assert result['importance_score'] == 0.98

    @pytest.mark.asyncio
    async def test_add_memory_below_short_term_threshold(
            self, storage_service, mock_importance_scorer):
        """Test adding memory with importance below short-term threshold defaults to short-term."""
        mock_importance_scorer.calculate_importance.return_value = 0.5  # Below 0.7

        result = await storage_service.add_memory(
            content="Low importance content"
        )

        assert result['success'] is True
        assert result['collection'] == 'short_term'

    @pytest.mark.asyncio
    async def test_add_memory_explicit_short_term(
            self, storage_service, mock_importance_scorer):
        """Test explicitly adding memory to short-term collection."""
        mock_importance_scorer.calculate_importance.return_value = 0.98  # Would be long-term if auto

        result = await storage_service.add_memory(
            content="High importance content",
            memory_type="short_term"
        )

        assert result['success'] is True
        assert result['collection'] == 'short_term'

    @pytest.mark.asyncio
    async def test_add_memory_explicit_long_term(
            self, storage_service, mock_importance_scorer):
        """Test explicitly adding memory to long-term collection."""
        mock_importance_scorer.calculate_importance.return_value = 0.5  # Would be short-term if auto

        result = await storage_service.add_memory(
            content="Low importance but forced long-term",
            memory_type="long_term"
        )

        assert result['success'] is True
        assert result['collection'] == 'long_term'

    @pytest.mark.asyncio
    async def test_add_memory_with_none_metadata(self, storage_service):
        """Test adding memory with None metadata."""
        result = await storage_service.add_memory(
            content="Content without metadata",
            metadata=None
        )

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_add_memory_with_context(
            self, storage_service, mock_chunk_manager):
        """Test adding memory with context data."""
        context = {'session_id': '123', 'user_intent': 'learning'}

        result = await storage_service.add_memory(
            content="Content with context",
            context=context
        )

        assert result['success'] is True
        # Verify chunk_manager was called with context in metadata
        call_args = mock_chunk_manager.create_document_with_relationships.call_args
        metadata = call_args.kwargs['metadata']
        assert 'context' in metadata
        assert json.loads(metadata['context']) == context

    @pytest.mark.asyncio
    async def test_add_memory_with_lifecycle_manager(
            self, storage_service_with_lifecycle, mock_lifecycle_manager):
        """Test adding memory with lifecycle manager enabled."""
        result = await storage_service_with_lifecycle.add_memory(
            content="Content with lifecycle processing"
        )

        assert result['success'] is True
        mock_lifecycle_manager.process_document_lifecycle.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_memory_enhanced_metadata(
            self, storage_service, mock_chunk_manager):
        """Test that enhanced metadata is properly added."""
        before_time = time.time()

        await storage_service.add_memory(
            content="Test content",
            metadata={'custom_field': 'value'}
        )

        after_time = time.time()

        call_args = mock_chunk_manager.create_document_with_relationships.call_args
        metadata = call_args.kwargs['metadata']

        assert metadata['custom_field'] == 'value'
        assert before_time <= metadata['timestamp'] <= after_time
        assert metadata['access_count'] == 0
        assert before_time <= metadata['last_accessed'] <= after_time
        assert 'importance_score' in metadata
        assert 'collection_type' in metadata

    @pytest.mark.asyncio
    async def test_add_memory_deduplication_boost_existing(
            self, storage_service, mock_deduplicator):
        """Test deduplication boosting existing document."""
        mock_deduplicator.enabled = True
        existing_doc = {'id': 'existing_123', 'content': 'similar content'}
        mock_deduplicator.check_ingestion_duplicates = AsyncMock(
            return_value=('boost_existing', existing_doc, 0.95)
        )

        result = await storage_service.add_memory(
            content="Similar content to existing"
        )

        assert result['success'] is True
        assert result['action'] == 'boosted_existing'
        assert result['similarity_score'] == 0.95
        assert result['chunks_added'] == 0
        mock_deduplicator.boost_existing_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_memory_deduplication_merge_content(
            self, storage_service, mock_deduplicator):
        """Test deduplication with merge content action still adds new document."""
        mock_deduplicator.enabled = True
        existing_doc = {'id': 'existing_123'}
        mock_deduplicator.check_ingestion_duplicates = AsyncMock(
            return_value=('merge_content', existing_doc, 0.85)
        )

        result = await storage_service.add_memory(
            content="Content that could be merged"
        )

        assert result['success'] is True
        assert result['action'] == 'added'

    @pytest.mark.asyncio
    async def test_add_memory_deduplication_add_new(
            self, storage_service, mock_deduplicator):
        """Test deduplication allows adding new document."""
        mock_deduplicator.enabled = True
        mock_deduplicator.check_ingestion_duplicates = AsyncMock(
            return_value=('add_new', None, 0.0)
        )

        result = await storage_service.add_memory(
            content="Unique content"
        )

        assert result['success'] is True
        assert result['action'] == 'added'

    @pytest.mark.asyncio
    async def test_add_memory_chroma_error(
            self, storage_service, mock_short_term_memory):
        """Test handling ChromaDB error."""
        # Import and use the actual ChromaError if available, otherwise use
        # Exception
        try:
            from chromadb.errors import ChromaError
            error = ChromaError("Database error")
        except ImportError:
            error = Exception("Database error")

        mock_short_term_memory.add_documents.side_effect = error

        result = await storage_service.add_memory(
            content="Content that causes error"
        )

        assert result['success'] is False
        assert 'error' in result
        assert result['chunks_added'] == 0

    @pytest.mark.asyncio
    async def test_add_memory_os_error(
            self, storage_service, mock_short_term_memory):
        """Test handling OSError."""
        mock_short_term_memory.add_documents.side_effect = OSError("Disk full")

        result = await storage_service.add_memory(
            content="Content that causes OS error"
        )

        assert result['success'] is False
        assert result['error_type'] == 'filesystem'
        assert 'Disk full' in result['error']

    @pytest.mark.asyncio
    async def test_add_memory_io_error(
            self, storage_service, mock_short_term_memory):
        """Test handling IOError."""
        mock_short_term_memory.add_documents.side_effect = IOError(
            "IO failure")

        result = await storage_service.add_memory(
            content="Content that causes IO error"
        )

        assert result['success'] is False
        assert result['error_type'] == 'filesystem'

    @pytest.mark.asyncio
    async def test_add_memory_unexpected_error(
            self, storage_service, mock_short_term_memory):
        """Test handling unexpected errors."""
        mock_short_term_memory.add_documents.side_effect = ValueError(
            "Unexpected error")

        result = await storage_service.add_memory(
            content="Content that causes unexpected error"
        )

        assert result['success'] is False
        assert result['error_type'] == 'unknown'


class TestChunkContent:
    """Tests for _chunk_content method."""

    def test_chunk_content_plain_text(self, storage_service):
        """Test chunking plain text content."""
        content = "This is a test. " * 100  # Create content long enough to chunk

        chunks = storage_service._chunk_content(content, "text")

        assert isinstance(chunks, list)
        assert len(chunks) >= 1
        # All chunks should be non-empty
        for chunk in chunks:
            assert len(chunk) > 0

    def test_chunk_content_python(self, storage_service):
        """Test chunking Python code."""
        content = """
def hello():
    print("Hello, World!")

class MyClass:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1
""" * 20

        chunks = storage_service._chunk_content(content, "python")

        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_chunk_content_javascript(self, storage_service):
        """Test chunking JavaScript code."""
        content = """
function hello() {
    console.log("Hello, World!");
}

class MyClass {
    constructor() {
        this.value = 0;
    }
}
""" * 20

        chunks = storage_service._chunk_content(content, "javascript")

        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_chunk_content_typescript(self, storage_service):
        """Test chunking TypeScript code (uses JS splitter)."""
        content = """
interface User {
    name: string;
    age: number;
}

function greet(user: User): string {
    return `Hello, ${user.name}!`;
}
""" * 20

        chunks = storage_service._chunk_content(content, "typescript")

        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_chunk_content_markdown(self, storage_service):
        """Test chunking Markdown content."""
        content = """
# Heading 1

This is some text under heading 1.

## Heading 2

More text here with some **bold** and *italic* formatting.

- List item 1
- List item 2
- List item 3
""" * 20

        chunks = storage_service._chunk_content(content, "markdown")

        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_chunk_content_html(self, storage_service):
        """Test chunking HTML content."""
        content = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Welcome</h1>
    <p>This is a paragraph.</p>
</body>
</html>
""" * 20

        chunks = storage_service._chunk_content(content, "html")

        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_chunk_content_java(self, storage_service):
        """Test chunking Java code."""
        content = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
""" * 20

        chunks = storage_service._chunk_content(content, "java")

        assert isinstance(chunks, list)

    def test_chunk_content_cpp(self, storage_service):
        """Test chunking C++ code."""
        content = """
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
""" * 20

        chunks = storage_service._chunk_content(content, "cpp")

        assert isinstance(chunks, list)

    def test_chunk_content_go(self, storage_service):
        """Test chunking Go code."""
        content = """
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
""" * 20

        chunks = storage_service._chunk_content(content, "go")

        assert isinstance(chunks, list)

    def test_chunk_content_rust(self, storage_service):
        """Test chunking Rust code."""
        content = """
fn main() {
    println!("Hello, World!");
}
""" * 20

        chunks = storage_service._chunk_content(content, "rust")

        assert isinstance(chunks, list)

    def test_chunk_content_ruby(self, storage_service):
        """Test chunking Ruby code."""
        content = """
class Greeter
  def initialize(name)
    @name = name
  end

  def greet
    puts "Hello, #{@name}!"
  end
end
""" * 20

        chunks = storage_service._chunk_content(content, "ruby")

        assert isinstance(chunks, list)

    def test_chunk_content_php(self, storage_service):
        """Test chunking PHP code."""
        content = """
<?php
class HelloWorld {
    public function greet() {
        echo "Hello, World!";
    }
}
?>
""" * 20

        chunks = storage_service._chunk_content(content, "php")

        assert isinstance(chunks, list)

    def test_chunk_content_unknown_language(self, storage_service):
        """Test chunking with unknown language falls back to default splitter."""
        content = "This is content in an unknown language format. " * 100

        chunks = storage_service._chunk_content(content, "unknown_lang")

        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_chunk_content_case_insensitive(self, storage_service):
        """Test language detection is case-insensitive."""
        content = "def test(): pass\n" * 100

        chunks_lower = storage_service._chunk_content(content, "python")
        chunks_upper = storage_service._chunk_content(content, "PYTHON")
        chunks_mixed = storage_service._chunk_content(content, "Python")

        # All should use the same splitter
        assert len(chunks_lower) == len(chunks_upper) == len(chunks_mixed)

    def test_chunk_content_short_content_single_chunk(self, storage_service):
        """Test that short content results in single chunk."""
        content = "Short content"

        chunks = storage_service._chunk_content(content, "text")

        assert len(chunks) == 1
        assert chunks[0] == content

    def test_chunk_content_empty_content(self, storage_service):
        """Test chunking empty content."""
        content = ""

        chunks = storage_service._chunk_content(content, "text")

        assert isinstance(chunks, list)

    def test_chunk_content_json(self, storage_service):
        """Test chunking JSON content (uses markdown splitter)."""
        content = json.dumps(
            {"key": "value", "nested": {"a": 1, "b": 2}}) * 100

        chunks = storage_service._chunk_content(content, "json")

        assert isinstance(chunks, list)

    def test_chunk_content_yaml(self, storage_service):
        """Test chunking YAML content (uses markdown splitter)."""
        content = """
name: test
version: 1.0
dependencies:
  - package1
  - package2
""" * 50

        chunks = storage_service._chunk_content(content, "yaml")

        assert isinstance(chunks, list)

    def test_chunk_content_xml(self, storage_service):
        """Test chunking XML content (uses HTML splitter)."""
        content = """
<?xml version="1.0"?>
<root>
    <item>Value 1</item>
    <item>Value 2</item>
</root>
""" * 50

        chunks = storage_service._chunk_content(content, "xml")

        assert isinstance(chunks, list)

    def test_chunk_content_c(self, storage_service):
        """Test chunking C code (uses CPP splitter)."""
        content = """
#include <stdio.h>

int main() {
    printf("Hello, World!");
    return 0;
}
""" * 20

        chunks = storage_service._chunk_content(content, "c")

        assert isinstance(chunks, list)


class TestFilterComplexMetadata:
    """Tests for _filter_complex_metadata method."""

    def test_filter_simple_types(self, storage_service):
        """Test that simple types are preserved."""
        metadata = {
            'string_field': 'value',
            'int_field': 42,
            'float_field': 3.14,
            'bool_field': True
        }

        filtered = storage_service._filter_complex_metadata(metadata)

        assert filtered == metadata

    def test_filter_list_to_json(self, storage_service):
        """Test that lists are converted to JSON strings."""
        metadata = {
            'list_field': [1, 2, 3],
            'nested_list': ['a', 'b', 'c']
        }

        filtered = storage_service._filter_complex_metadata(metadata)

        assert filtered['list_field'] == '[1, 2, 3]'
        assert filtered['nested_list'] == '["a", "b", "c"]'

    def test_filter_dict_to_json(self, storage_service):
        """Test that dicts are converted to JSON strings."""
        metadata = {
            'dict_field': {'nested': 'value'},
            'complex_dict': {'a': 1, 'b': {'c': 2}}
        }

        filtered = storage_service._filter_complex_metadata(metadata)

        assert json.loads(filtered['dict_field']) == {'nested': 'value'}
        assert json.loads(filtered['complex_dict']) == {'a': 1, 'b': {'c': 2}}

    def test_filter_none_to_empty_string(self, storage_service):
        """Test that None values are converted to empty strings."""
        metadata = {
            'none_field': None,
            'valid_field': 'value'
        }

        filtered = storage_service._filter_complex_metadata(metadata)

        assert filtered['none_field'] == ''
        assert filtered['valid_field'] == 'value'

    def test_filter_custom_object_to_string(self, storage_service):
        """Test that custom objects are converted to strings."""
        class CustomObject:
            def __str__(self):
                return "CustomObject()"

        metadata = {
            'custom_field': CustomObject()
        }

        filtered = storage_service._filter_complex_metadata(metadata)

        assert filtered['custom_field'] == "CustomObject()"

    def test_filter_non_serializable_to_string(self, storage_service):
        """Test that non-JSON-serializable objects fall back to str()."""
        class NonSerializable:
            def __str__(self):
                return "non_serializable"

        metadata = {
            'weird_list': [NonSerializable(), NonSerializable()]
        }

        filtered = storage_service._filter_complex_metadata(metadata)

        # Should fall back to str() for the list
        assert isinstance(filtered['weird_list'], str)

    def test_filter_empty_metadata(self, storage_service):
        """Test filtering empty metadata."""
        metadata = {}

        filtered = storage_service._filter_complex_metadata(metadata)

        assert filtered == {}

    def test_filter_mixed_metadata(self, storage_service):
        """Test filtering metadata with mixed types."""
        metadata = {
            'string': 'text',
            'number': 123,
            'float': 1.5,
            'boolean': False,
            'list': [1, 2],
            'dict': {'key': 'val'},
            'none': None
        }

        filtered = storage_service._filter_complex_metadata(metadata)

        assert filtered['string'] == 'text'
        assert filtered['number'] == 123
        assert filtered['float'] == 1.5
        assert filtered['boolean'] is False
        assert filtered['list'] == '[1, 2]'
        assert filtered['dict'] == '{"key": "val"}'
        assert filtered['none'] == ''

    def test_filter_preserves_original(self, storage_service):
        """Test that original metadata is not modified."""
        original = {
            'list_field': [1, 2, 3],
            'dict_field': {'nested': 'value'}
        }
        original_copy = {
            'list_field': [1, 2, 3],
            'dict_field': {'nested': 'value'}
        }

        storage_service._filter_complex_metadata(original)

        assert original == original_copy


class TestRemoveDocumentsFromCollection:
    """Tests for remove_documents_from_collection method."""

    def test_remove_documents_with_chroma_id(
            self, storage_service, mock_short_term_memory):
        """Test removing documents using chroma_id."""
        docs_to_remove = [
            Mock(page_content="content1", metadata={'chroma_id': 'id_1'}),
            Mock(page_content="content2", metadata={'chroma_id': 'id_2'})
        ]

        storage_service.remove_documents_from_collection(
            mock_short_term_memory, docs_to_remove)

        mock_short_term_memory._collection.delete.assert_called_once_with(ids=[
                                                                          'id_1', 'id_2'])

    def test_remove_documents_with_id_fallback(
            self, storage_service, mock_short_term_memory):
        """Test removing documents using id when chroma_id is not available."""
        docs_to_remove = [
            Mock(page_content="content1", metadata={'id': 'fallback_id_1'}),
            Mock(page_content="content2", metadata={'id': 'fallback_id_2'})
        ]

        storage_service.remove_documents_from_collection(
            mock_short_term_memory, docs_to_remove)

        mock_short_term_memory._collection.delete.assert_called_once_with(
            ids=['fallback_id_1', 'fallback_id_2']
        )

    def test_remove_documents_with_hash_fallback(
            self, storage_service, mock_short_term_memory):
        """Test removing documents using content hash when no id is available."""
        docs_to_remove = [
            Mock(page_content="content1", metadata={}),
            Mock(page_content="content2", metadata={})
        ]

        storage_service.remove_documents_from_collection(
            mock_short_term_memory, docs_to_remove)

        # Verify delete was called (with hashes)
        mock_short_term_memory._collection.delete.assert_called_once()
        call_args = mock_short_term_memory._collection.delete.call_args
        assert len(call_args.kwargs['ids']) == 2

    def test_remove_documents_empty_list(
            self, storage_service, mock_short_term_memory):
        """Test removing empty list of documents does not call delete."""
        docs_to_remove = []

        storage_service.remove_documents_from_collection(
            mock_short_term_memory, docs_to_remove)

        mock_short_term_memory._collection.delete.assert_not_called()

    def test_remove_documents_no_collection_attribute(self, storage_service):
        """Test that removal is skipped when collection lacks _collection attribute."""
        collection_without_attr = Mock(
            spec=[])  # Empty spec means no _collection
        docs_to_remove = [
            Mock(page_content="content1", metadata={'chroma_id': 'id_1'})
        ]

        # Should not raise an error
        storage_service.remove_documents_from_collection(
            collection_without_attr, docs_to_remove)

    def test_remove_documents_delete_error(
            self, storage_service, mock_short_term_memory):
        """Test handling delete errors without data loss."""
        mock_short_term_memory._collection.delete.side_effect = Exception(
            "Delete failed")
        docs_to_remove = [
            Mock(page_content="content1", metadata={'chroma_id': 'id_1'})
        ]

        # Should not raise an error, just log it
        storage_service.remove_documents_from_collection(
            mock_short_term_memory, docs_to_remove)

        # Delete should have been attempted
        mock_short_term_memory._collection.delete.assert_called_once()

    def test_remove_documents_mixed_id_sources(
            self, storage_service, mock_short_term_memory):
        """Test removing documents with mixed id sources."""
        docs_to_remove = [
            Mock(page_content="content1", metadata={'chroma_id': 'chroma_1'}),
            Mock(page_content="content2", metadata={'id': 'id_2'}),
            Mock(page_content="content3", metadata={})  # Will use hash
        ]

        storage_service.remove_documents_from_collection(
            mock_short_term_memory, docs_to_remove)

        call_args = mock_short_term_memory._collection.delete.call_args
        ids = call_args.kwargs['ids']
        assert len(ids) == 3
        assert 'chroma_1' in ids
        assert 'id_2' in ids

    def test_remove_documents_from_long_term(
            self, storage_service, mock_long_term_memory):
        """Test removing documents from long-term collection."""
        docs_to_remove = [
            Mock(page_content="important content",
                 metadata={'chroma_id': 'lt_id_1'})
        ]

        storage_service.remove_documents_from_collection(
            mock_long_term_memory, docs_to_remove)

        mock_long_term_memory._collection.delete.assert_called_once_with(ids=[
                                                                         'lt_id_1'])


class TestIntegrationScenarios:
    """Integration-style tests for combined functionality."""

    @pytest.mark.asyncio
    async def test_full_add_memory_flow(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_chunk_manager,
        mock_importance_scorer,
        mock_deduplicator,
        mock_lifecycle_manager
    ):
        """Test complete flow of adding memory with all features enabled."""
        mock_importance_scorer.calculate_importance.return_value = 0.85
        mock_deduplicator.enabled = True
        mock_deduplicator.check_ingestion_duplicates = AsyncMock(
            return_value=('add_new', None, 0.0)
        )

        service = MemoryStorageService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            chunk_manager=mock_chunk_manager,
            importance_scorer=mock_importance_scorer,
            deduplicator=mock_deduplicator,
            lifecycle_manager=mock_lifecycle_manager,
            config={
                'chunk_size': 500,
                'chunk_overlap': 50,
                'short_term_threshold': 0.7,
                'long_term_threshold': 0.95
            }
        )

        result = await service.add_memory(
            content="Test content for full flow",
            metadata={'source': 'test', 'tags': ['unit', 'test']},
            context={'session_id': 'test_session'}
        )

        assert result['success'] is True
        assert result['collection'] == 'short_term'

        # Verify all dependencies were called
        mock_importance_scorer.calculate_importance.assert_called_once()
        mock_deduplicator.check_ingestion_duplicates.assert_called_once()
        mock_lifecycle_manager.process_document_lifecycle.assert_called_once()
        mock_chunk_manager.create_document_with_relationships.assert_called_once()
        mock_short_term_memory.add_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_memory_with_complex_metadata_filtering(
        self,
        mock_short_term_memory,
        mock_long_term_memory,
        mock_chunk_manager,
        mock_importance_scorer,
        mock_deduplicator
    ):
        """Test that complex metadata is properly filtered before storage."""
        service = MemoryStorageService(
            short_term_memory=mock_short_term_memory,
            long_term_memory=mock_long_term_memory,
            chunk_manager=mock_chunk_manager,
            importance_scorer=mock_importance_scorer,
            deduplicator=mock_deduplicator
        )

        complex_metadata = {
            'simple': 'string',
            'nested': {'key': 'value'},
            'list': [1, 2, 3],
            'none_val': None
        }

        result = await service.add_memory(
            content="Content with complex metadata",
            metadata=complex_metadata
        )

        assert result['success'] is True

        # Verify the metadata passed to chunk_manager was filtered
        call_args = mock_chunk_manager.create_document_with_relationships.call_args
        filtered_metadata = call_args.kwargs['metadata']

        assert filtered_metadata['simple'] == 'string'
        assert isinstance(
            filtered_metadata['nested'],
            str)  # Should be JSON string
        assert isinstance(
            filtered_metadata['list'],
            str)  # Should be JSON string
        # None converted to empty string
        assert filtered_metadata['none_val'] == ''
