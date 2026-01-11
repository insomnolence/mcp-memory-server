"""
Chunk Relationship Manager (Facade)

Provides a unified interface for chunk relationship management, coordinating
between specialized services for:
- Persistence (serialization/deserialization, ChromaDB storage)
- Merge History (deduplication tracking)
- Query (retrieval and statistics)

This facade maintains backward compatibility with existing code while
delegating to focused service classes.
"""

import time
import logging
from typing import Dict, Any, List, Optional

from langchain_core.documents import Document

# Import ChromaDB errors for specific exception handling
try:
    from chromadb.errors import ChromaError
except ImportError:
    ChromaError = Exception

# Import services
from .services.relationship_persistence import (
    RelationshipPersistenceService,
    SYSTEM_DOC_TYPE_MERGE_HISTORY,
    FIELD_RELATED_CHUNKS,
    FIELD_DEDUP_SOURCES,
    FIELD_RELATIONSHIP_STRENGTH,
    FIELD_DEDUP_HISTORY,
    MAX_MERGE_HISTORY_SIZE,
    MAX_RELATIONSHIPS_PER_CHUNK,
)
from .services.merge_history import MergeHistoryService
from .services.relationship_query import RelationshipQueryService


class ChunkRelationshipManager:
    """Facade for chunk relationship management.

    Coordinates between specialized services while maintaining backward
    compatibility with existing code that depends on this class.
    """

    def __init__(self, memory_system, relationship_config: dict = None):
        """Initialize chunk relationship manager.

        Args:
            memory_system: Reference to HierarchicalMemorySystem
            relationship_config: Configuration for relationship management
        """
        self.memory_system = memory_system
        self.config = relationship_config or self._get_default_config()

        # Relationship tracking (shared state used by services)
        self.document_relationships: Dict[str, Any] = {}
        self.chunk_relationships: Dict[str, Any] = {}

        # Initialize services
        self._persistence_service = RelationshipPersistenceService(memory_system)

        self._merge_history_service = MergeHistoryService(
            persistence_service=self._persistence_service,
            chunk_relationships=self.chunk_relationships,
            document_relationships=self.document_relationships
        )

        self._query_service = RelationshipQueryService(
            memory_system=memory_system,
            chunk_relationships=self.chunk_relationships,
            document_relationships=self.document_relationships,
            merge_history_service=self._merge_history_service,
            config=self.config,
            load_chunk_callback=self._load_chunk_from_chromadb,
            load_document_callback=self._load_document_from_chromadb
        )

    # =========================================================================
    # Backward Compatibility Properties
    # =========================================================================

    @property
    def merge_history(self) -> Dict[str, Any]:
        """Access merge history (delegates to service)."""
        return self._merge_history_service.merge_history

    @property
    def _merge_history_loaded(self) -> bool:
        """Check if merge history is loaded."""
        return self._merge_history_service._merge_history_loaded

    # =========================================================================
    # Configuration
    # =========================================================================

    def _get_default_config(self) -> dict:
        """Default configuration for chunk relationships."""
        return {
            'enable_related_retrieval': True,
            'max_related_chunks': 3,
            'relationship_decay_days': 30,
            'track_merge_relationships': True,
            'preserve_original_context': True,
            'context_window_size': 2,
            'semantic_relationship_threshold': 0.7,
            'max_relationships_per_chunk': 5,
            'semantic_similarity_threshold': 0.8,
            'co_occurrence_window': 3
        }

    # =========================================================================
    # Delegated Methods (for backward compatibility)
    # =========================================================================

    # Serialization (delegate to persistence service)
    def _serialize_json(self, data: Any) -> str:
        return self._persistence_service.serialize_json(data)

    def _deserialize_json(self, json_str: str, default: Any = None) -> Any:
        return self._persistence_service.deserialize_json(json_str, default)

    def _serialize_chunk_relationships(self, chunk_id: str) -> Dict[str, str]:
        if chunk_id not in self.chunk_relationships:
            return {}
        return self._persistence_service.serialize_chunk_relationships(
            self.chunk_relationships[chunk_id]
        )

    def _deserialize_chunk_relationships(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return self._persistence_service.deserialize_chunk_relationships(metadata)

    # System documents (delegate to persistence service)
    def _get_system_document(self, doc_type: str) -> Optional[Dict[str, Any]]:
        return self._persistence_service.get_system_document(doc_type)

    def _save_system_document(self, doc_type: str, data: Dict[str, Any]) -> bool:
        return self._persistence_service.save_system_document(doc_type, data)

    # Merge history (delegate to merge history service)
    def _load_merge_history_from_storage(self) -> None:
        self._merge_history_service.load_from_storage()

    def _save_merge_history_to_storage(self) -> bool:
        return self._merge_history_service.save_to_storage()

    def handle_deduplication_merge(
        self,
        primary_doc_id: str,
        merged_doc_ids: List[str],
        similarity_scores: List[float]
    ) -> Dict[str, Any]:
        return self._merge_history_service.handle_deduplication_merge(
            primary_doc_id, merged_doc_ids, similarity_scores
        )

    def _get_merge_related_chunks(
        self,
        source_chunk_id: str,
        document_id: str,
        k_related: int
    ) -> List[Dict[str, Any]]:
        return self._merge_history_service.get_merge_related_chunks(
            source_chunk_id, document_id, k_related
        )

    # Query operations (delegate to query service)
    def retrieve_related_chunks(
        self,
        found_chunk_id: str,
        k_related: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        return self._query_service.retrieve_related_chunks(found_chunk_id, k_related)

    def get_document_context(self, document_id: str) -> Dict[str, Any]:
        return self._query_service.get_document_context(document_id)

    def get_relationship_statistics(self) -> Dict[str, Any]:
        return self._query_service.get_relationship_statistics()

    def _find_chunk_content_in_collections(self, chunk_id: str) -> Optional[str]:
        return self._query_service.find_chunk_content_in_collections(chunk_id)

    def cleanup_stale_references(
        self,
        deleted_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        return self._query_service.cleanup_stale_references(deleted_ids)

    # =========================================================================
    # Persistence (delegate to persistence service)
    # =========================================================================

    async def _persist_chunk_relationships(self, chunk_id: str) -> bool:
        """Persist a chunk's relationship data to ChromaDB."""
        if chunk_id not in self.chunk_relationships:
            return True
        return await self._persistence_service.persist_chunk_relationships(
            chunk_id, self.chunk_relationships[chunk_id]
        )

    # =========================================================================
    # Chunk/Document Loading (kept in facade for shared state access)
    # =========================================================================

    def _load_chunk_from_chromadb(self, chunk_id: str) -> bool:
        """Lazy load a chunk's relationship data from ChromaDB.

        Args:
            chunk_id: The chunk ID to load

        Returns:
            True if chunk was found and loaded, False otherwise
        """
        if chunk_id in self.chunk_relationships:
            return True

        try:
            for collection_name in ['short_term_memory', 'long_term_memory']:
                collection = getattr(self.memory_system, collection_name, None)
                if not collection or not hasattr(collection, '_collection'):
                    continue

                try:
                    result = collection._collection.get(where={'chunk_id': chunk_id})
                    if result and result.get('ids') and len(result['ids']) > 0:
                        metadata = result['metadatas'][0] if result.get('metadatas') else {}
                        content = result['documents'][0] if result.get('documents') else ''

                        doc_id = metadata.get('document_id', '')
                        chunk_index = metadata.get('chunk_index', 0)

                        # Deserialize persisted relationship data
                        persisted_data = self._deserialize_chunk_relationships(metadata)

                        self.chunk_relationships[chunk_id] = {
                            'chunk_id': chunk_id,
                            'document_id': doc_id,
                            'chunk_index': chunk_index,
                            'content_preview': (
                                content[:100] + '...' if len(content) > 100 else content
                            ),
                            'related_chunks': persisted_data.get('related_chunks', []),
                            'deduplication_sources': persisted_data.get(
                                'deduplication_sources', []
                            ),
                            'access_history': [],
                            'relationship_strength': persisted_data.get(
                                'relationship_strength', {}
                            ),
                            'complex_relationships': {
                                'previous_chunk': metadata.get('previous_chunk'),
                                'next_chunk': metadata.get('next_chunk'),
                                'document_start': metadata.get('document_start', False),
                                'document_end': metadata.get('document_end', False),
                                'relative_position': metadata.get('relative_position', 0.0),
                                'context_window': {
                                    'start_chunk': metadata.get('context_start_chunk', 0),
                                    'end_chunk': metadata.get('context_end_chunk', 0)
                                }
                            }
                        }

                        if doc_id and doc_id not in self.document_relationships:
                            self._load_document_from_chromadb(doc_id)

                        logging.debug(f"Lazy loaded chunk {chunk_id} from {collection_name}")
                        return True
                except Exception as e:
                    logging.debug(f"Error loading chunk {chunk_id} from {collection_name}: {e}")
                    continue

        except Exception as e:
            logging.warning(f"Failed to lazy load chunk {chunk_id}: {e}")

        return False

    def _load_document_from_chromadb(self, document_id: str) -> bool:
        """Lazy load a document's relationship data from ChromaDB.

        Args:
            document_id: The document ID to load

        Returns:
            True if document was found and loaded, False otherwise
        """
        if document_id in self.document_relationships:
            return True

        try:
            for collection_name in ['short_term_memory', 'long_term_memory']:
                collection = getattr(self.memory_system, collection_name, None)
                if not collection or not hasattr(collection, '_collection'):
                    continue

                try:
                    result = collection._collection.get(where={'document_id': document_id})
                    if result and result.get('ids') and len(result['ids']) > 0:
                        first_metadata = result['metadatas'][0] if result.get('metadatas') else {}
                        chunk_ids = result['ids']
                        total_chunks = first_metadata.get('total_chunks', len(chunk_ids))

                        # Deserialize deduplication history
                        dedup_history = self._deserialize_json(
                            first_metadata.get(FIELD_DEDUP_HISTORY, ''), default=[]
                        )

                        self.document_relationships[document_id] = {
                            'document_id': document_id,
                            'original_content_length': 0,
                            'chunk_count': total_chunks,
                            'creation_time': first_metadata.get('creation_timestamp', 0),
                            'collection': collection_name.replace('_memory', ''),
                            'content_hash': 0,
                            'language': first_metadata.get('language', 'text'),
                            'source_metadata': {},
                            'deduplication_history': dedup_history,
                            'related_documents': [],
                            'chunk_ids': chunk_ids
                        }

                        logging.debug(
                            f"Lazy loaded document {document_id} with "
                            f"{len(chunk_ids)} chunks from {collection_name}"
                        )
                        return True
                except Exception as e:
                    logging.debug(
                        f"Error loading document {document_id} from {collection_name}: {e}"
                    )
                    continue

        except Exception as e:
            logging.warning(f"Failed to lazy load document {document_id}: {e}")

        return False

    # =========================================================================
    # Document Creation and Relationship Building
    # =========================================================================

    async def create_document_with_relationships(
        self,
        content: str,
        metadata: dict,
        chunks: List[str],
        memory_id: str,
        collection_name: str
    ) -> List[Document]:
        """Create documents with enhanced relationship tracking.

        Args:
            content: Original document content
            metadata: Document metadata
            chunks: List of content chunks
            memory_id: Unique document ID
            collection_name: Target collection name

        Returns:
            List of Document objects with relationship metadata
        """
        current_time = time.time()

        # Create document relationship record
        document_relationship = {
            'document_id': memory_id,
            'original_content_length': len(content),
            'chunk_count': len(chunks),
            'creation_time': current_time,
            'collection': collection_name,
            'content_hash': hash(content),
            'language': metadata.get('language', 'text'),
            'source_metadata': metadata.copy(),
            'deduplication_history': [],
            'related_documents': [],
            'chunk_ids': []
        }

        documents = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{memory_id}_chunk_{i}"

            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunks),
                'chunk_id': chunk_id,
                'document_id': memory_id,
                'memory_id': memory_id,
                'collection_name': collection_name,
                'previous_chunk': f"{memory_id}_chunk_{i - 1}" if i > 0 else None,
                'next_chunk': (
                    f"{memory_id}_chunk_{i + 1}" if i < len(chunks) - 1 else None
                ),
                'document_start': i == 0,
                'document_end': i == len(chunks) - 1,
                'relative_position': i / max(len(chunks) - 1, 1),
                'context_start_chunk': max(0, i - self.config['context_window_size']),
                'context_end_chunk': min(
                    len(chunks) - 1, i + self.config['context_window_size']
                ),
                'document_summary': self._generate_document_summary(content),
                'creation_timestamp': current_time,
                'relationship_version': '1.0'
            })

            complex_relationships = {
                'previous_chunk': f"{memory_id}_chunk_{i - 1}" if i > 0 else None,
                'next_chunk': (
                    f"{memory_id}_chunk_{i + 1}" if i < len(chunks) - 1 else None
                ),
                'document_start': i == 0,
                'document_end': i == len(chunks) - 1,
                'relative_position': i / max(len(chunks) - 1, 1),
                'context_window': {
                    'start_chunk': max(0, i - self.config['context_window_size']),
                    'end_chunk': min(
                        len(chunks) - 1, i + self.config['context_window_size']
                    )
                }
            }

            self.chunk_relationships[chunk_id] = {
                'chunk_id': chunk_id,
                'document_id': memory_id,
                'chunk_index': i,
                'content_preview': chunk[:100] + '...' if len(chunk) > 100 else chunk,
                'related_chunks': [],
                'deduplication_sources': [],
                'access_history': [],
                'relationship_strength': {},
                'complex_relationships': complex_relationships
            }

            document_relationship['chunk_ids'].append(chunk_id)
            documents.append(Document(page_content=chunk, metadata=chunk_metadata))

        self.document_relationships[memory_id] = document_relationship

        for doc in documents:
            chunk_id = doc.metadata.get('chunk_id')
            if chunk_id and chunk_id not in self.chunk_relationships:
                logging.warning(
                    f"Chunk relationship for {chunk_id} was not stored properly"
                )

        if self.config['enable_related_retrieval']:
            try:
                await self._establish_semantic_relationships(memory_id, content, documents)
            except Exception as e:
                logging.warning(
                    f"Failed to establish semantic relationships for {memory_id}: {e}"
                )

        return documents

    def _generate_document_summary(self, content: str) -> str:
        """Generate a summary of the document for relationship context."""
        sentences = content.split('. ')
        if sentences and len(sentences[0]) > 50:
            return sentences[0] + ('.' if not sentences[0].endswith('.') else '')
        else:
            return content[:200] + '...' if len(content) > 200 else content

    async def _establish_semantic_relationships(
        self,
        new_document_id: str,
        content: str,
        new_documents: List[Document]
    ):
        """Find and establish relationships with semantically similar documents."""
        try:
            similar_results = await self.memory_system.query_memories(
                content[:500],
                k=5,
                use_smart_routing=False
            )

            if 'content' not in similar_results:
                return

            for result_block in similar_results['content']:
                try:
                    result_text = result_block.get('text', '')
                    if 'Metadata:' in result_text:
                        pass
                except Exception as e:
                    logging.warning(f"Failed to establish relationship from result: {e}")
                    continue

        except Exception as e:
            logging.warning(f"Failed to establish semantic relationships: {e}")

    async def _update_relationships_semantic(
        self,
        doc: Document,
        candidates: List[Document],
        collection_name: str
    ):
        """Update semantic relationships between documents and persist."""
        chunk_id = doc.metadata.get('chunk_id')
        if not chunk_id:
            return

        relationships_added = False

        for candidate in candidates:
            similarity = self.memory_system.deduplicator.similarity_calculator.calculate_similarity(
                doc.page_content, candidate.page_content
            )

            if similarity >= self.config['semantic_similarity_threshold']:
                relationship = {
                    'target_chunk_id': candidate.metadata.get('chunk_id'),
                    'type': 'semantic_similarity',
                    'score': similarity,
                    'context_relevance': min(1.0, similarity + 0.1)
                }
                if chunk_id in self.chunk_relationships:
                    if 'related_chunks' not in self.chunk_relationships[chunk_id]:
                        self.chunk_relationships[chunk_id]['related_chunks'] = []
                    self.chunk_relationships[chunk_id]['related_chunks'].append(relationship)
                    relationships_added = True

        if relationships_added:
            await self._persist_chunk_relationships(chunk_id)

    async def _update_relationships_co_occurrence(
        self,
        docs: List[Document],
        collection_name: str
    ):
        """Update co-occurrence relationships between documents."""
        doc_terms = []
        for doc in docs:
            terms = set(doc.page_content.lower().split())
            doc_terms.append(terms)

        chunks_to_persist = []

        for i, doc1 in enumerate(docs):
            doc1_terms = doc_terms[i]
            relationships = []

            for j, doc2 in enumerate(docs):
                if i != j:
                    doc2_terms = doc_terms[j]
                    common_terms = doc1_terms.intersection(doc2_terms)

                    if len(common_terms) >= 2:
                        co_occurrence_score = len(common_terms) / len(
                            doc1_terms.union(doc2_terms)
                        )
                        relationship = {
                            'target_chunk_id': doc2.metadata.get('chunk_id'),
                            'type': 'co_occurrence',
                            'score': co_occurrence_score,
                            'common_terms': list(common_terms)[:10]
                        }
                        relationships.append(relationship)

            if relationships:
                chunk_id = doc1.metadata.get('chunk_id')
                if chunk_id and chunk_id in self.chunk_relationships:
                    if 'related_chunks' not in self.chunk_relationships[chunk_id]:
                        self.chunk_relationships[chunk_id]['related_chunks'] = []
                    self.chunk_relationships[chunk_id]['related_chunks'].extend(relationships)
                    chunks_to_persist.append(chunk_id)

        for chunk_id in chunks_to_persist:
            await self._persist_chunk_relationships(chunk_id)
