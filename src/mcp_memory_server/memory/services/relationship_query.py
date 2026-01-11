"""
Relationship Query Service

Handles querying and retrieving relationship data, including:
- Related chunk retrieval
- Document context retrieval
- Relationship statistics
- Stale reference cleanup
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable


class RelationshipQueryService:
    """Service for querying relationship data.

    Provides methods for retrieving related chunks, document context,
    and relationship statistics.
    """

    def __init__(
        self,
        memory_system,
        chunk_relationships: Dict[str, Any],
        document_relationships: Dict[str, Any],
        merge_history_service,
        config: Dict[str, Any],
        load_chunk_callback: Callable[[str], bool],
        load_document_callback: Callable[[str], bool]
    ):
        """Initialize the query service.

        Args:
            memory_system: Reference to HierarchicalMemorySystem
            chunk_relationships: Reference to chunk relationships dict
            document_relationships: Reference to document relationships dict
            merge_history_service: Service for merge history operations
            config: Configuration dict with query settings
            load_chunk_callback: Callback to lazy load a chunk
            load_document_callback: Callback to lazy load a document
        """
        self.memory_system = memory_system
        self.chunk_relationships = chunk_relationships
        self.document_relationships = document_relationships
        self.merge_history_service = merge_history_service
        self.config = config
        self._load_chunk = load_chunk_callback
        self._load_document = load_document_callback

    def retrieve_related_chunks(
        self,
        found_chunk_id: str,
        k_related: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get related chunks when one chunk is found relevant.

        Args:
            found_chunk_id: ID of the chunk that was found relevant
            k_related: Number of related chunks to retrieve (default from config)

        Returns:
            List of related chunk information with context
        """
        if k_related is None:
            k_related = self.config.get('max_related_chunks', 3)

        # Lazy load chunk if not in cache
        if not self._load_chunk(found_chunk_id):
            logging.warning(f"Chunk {found_chunk_id} not found in ChromaDB")
            return []

        chunk_rel = self.chunk_relationships[found_chunk_id]
        document_id = chunk_rel['document_id']

        # Ensure document is loaded for chunk count info
        self._load_document(document_id)

        related_chunks = []

        try:
            # Get adjacent chunks from same document
            if document_id in self.document_relationships:
                doc_rel = self.document_relationships[document_id]
                chunk_index = chunk_rel['chunk_index']

                # Calculate range of related chunks
                start_idx = max(0, chunk_index - k_related // 2)
                end_idx = min(doc_rel['chunk_count'], chunk_index + k_related // 2 + 1)

                for i in range(start_idx, end_idx):
                    if i != chunk_index:
                        related_chunk_id = f"{document_id}_chunk_{i}"
                        if self._load_chunk(related_chunk_id):
                            related_rel = self.chunk_relationships[related_chunk_id]
                            related_chunks.append({
                                'chunk_id': related_chunk_id,
                                'document_id': document_id,
                                'chunk_index': i,
                                'relationship_type': 'adjacent',
                                'distance_from_source': abs(i - chunk_index),
                                'content_preview': related_rel['content_preview'],
                                'deduplication_sources': related_rel['deduplication_sources'],
                                'context_relevance': 1.0 - (abs(i - chunk_index) / k_related)
                            })

            # Get semantic relationships from related_chunks field
            semantic_related = chunk_rel.get('related_chunks', [])
            for rel in semantic_related:
                target_chunk_id = rel.get('target_chunk_id')
                if target_chunk_id and self._load_chunk(target_chunk_id):
                    target_rel = self.chunk_relationships[target_chunk_id]
                    related_chunks.append({
                        'chunk_id': target_chunk_id,
                        'document_id': target_rel.get('document_id', 'unknown'),
                        'chunk_index': target_rel.get('chunk_index', 0),
                        'relationship_type': rel.get('type', 'semantic'),
                        'content_preview': target_rel.get('content_preview', 'No preview'),
                        'context_relevance': rel.get(
                            'context_relevance', rel.get('score', 0.0)
                        )
                    })

            # Get chunks from merged documents (deduplication-aware)
            merge_related_chunks = self.merge_history_service.get_merge_related_chunks(
                found_chunk_id, document_id, k_related
            )
            related_chunks.extend(merge_related_chunks)

            # Sort by relevance and limit results
            related_chunks.sort(key=lambda x: x.get('context_relevance', 0), reverse=True)
            return related_chunks[:k_related]

        except Exception as e:
            logging.error(f"Failed to retrieve related chunks for {found_chunk_id}: {e}")
            return []

    def get_document_context(self, document_id: str) -> Dict[str, Any]:
        """Get comprehensive context for a document including relationships and history.

        Args:
            document_id: The document ID to get context for

        Returns:
            Dictionary with document context information
        """
        # Lazy load document if not in cache
        if not self._load_document(document_id):
            return {'error': 'Document not found in ChromaDB'}

        doc_rel = self.document_relationships[document_id]
        current_time = time.time()

        context = {
            'document_id': document_id,
            'creation_time': doc_rel['creation_time'],
            'age_days': (current_time - doc_rel['creation_time']) / 86400,
            'chunk_count': doc_rel['chunk_count'],
            'collection': doc_rel['collection'],
            'language': doc_rel['language'],
            'deduplication_history': doc_rel.get('deduplication_history', []),
            'related_documents': doc_rel.get('related_documents', []),
            'consolidation_info': {}
        }

        # Add consolidation information if applicable
        if 'consolidated_chunk_count' in doc_rel:
            context['consolidation_info'] = {
                'is_consolidated': True,
                'original_chunk_count': doc_rel['chunk_count'],
                'total_consolidated_chunks': doc_rel['consolidated_chunk_count'],
                'consolidation_ratio': (
                    doc_rel['consolidated_chunk_count'] / doc_rel['chunk_count']
                ),
                'merge_benefit_score': doc_rel.get('merge_benefit_score', 0.0)
            }

        # Add merge history details
        merge_count = len(doc_rel.get('deduplication_history', []))
        if merge_count > 0:
            context['merge_statistics'] = {
                'total_merges': merge_count,
                'documents_absorbed': sum(
                    len(merge.get('source_documents', []))
                    for merge in doc_rel['deduplication_history']
                ),
                'latest_merge': max(
                    merge['merge_timestamp']
                    for merge in doc_rel['deduplication_history']
                ) if doc_rel['deduplication_history'] else None
            }

        return context

    def get_relationship_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about chunk relationships and deduplication.

        Returns:
            Dictionary with relationship statistics
        """
        # Ensure merge history is loaded
        self.merge_history_service.ensure_loaded()

        current_time = time.time()

        # Collect stats directly from ChromaDB
        total_chunks = 0
        unique_document_ids = set()
        document_chunk_counts = {}
        document_creation_times = {}
        total_relationships_found = 0
        relationship_types = {}

        try:
            for collection in ['short_term_memory', 'long_term_memory']:
                memory_collection = getattr(self.memory_system, collection, None)
                if memory_collection and hasattr(memory_collection, '_collection'):
                    try:
                        result = memory_collection._collection.get()
                        if result and 'metadatas' in result:
                            for metadata in result['metadatas']:
                                if metadata and isinstance(metadata, dict):
                                    total_chunks += 1

                                    doc_id = metadata.get('document_id')
                                    if doc_id:
                                        unique_document_ids.add(doc_id)
                                        total_in_doc = metadata.get('total_chunks', 1)
                                        document_chunk_counts[doc_id] = total_in_doc

                                        creation_time = metadata.get('creation_timestamp', 0)
                                        if (doc_id not in document_creation_times or
                                                creation_time < document_creation_times[doc_id]):
                                            document_creation_times[doc_id] = creation_time

                                    chunk_id = metadata.get('chunk_id')
                                    if chunk_id and chunk_id in self.chunk_relationships:
                                        chunk_rel = self.chunk_relationships[chunk_id]
                                        relationships = chunk_rel.get('related_chunks', [])
                                        if relationships:
                                            total_relationships_found += len(relationships)
                                            for rel in relationships:
                                                rel_type = rel.get('type', 'unknown')
                                                relationship_types[rel_type] = (
                                                    relationship_types.get(rel_type, 0) + 1
                                                )
                    except Exception as e:
                        logging.warning(f"Error accessing {collection}: {e}")
        except Exception as e:
            logging.warning(f"Error scanning collections for stats: {e}")
            total_chunks = len(self.chunk_relationships)
            unique_document_ids = set(self.document_relationships.keys())

        total_documents = len(unique_document_ids)

        avg_chunks = 0.0
        if document_chunk_counts:
            avg_chunks = sum(document_chunk_counts.values()) / len(document_chunk_counts)

        merge_stats = self.merge_history_service.get_statistics()

        stats = {
            'total_documents': total_documents,
            'total_chunks': total_chunks,
            'total_chunks_analyzed': total_chunks,
            'total_relationships_found': total_relationships_found,
            'relationship_types_distribution': relationship_types,
            'total_merges': merge_stats['total_merges'],
            'documents_with_merges': 0,
            'average_chunks_per_document': avg_chunks,
            'relationship_health': {},
            'deduplication_impact': {},
            'recent_activity': {}
        }

        # Count documents with merge history
        stats['documents_with_merges'] = sum(
            1 for doc in self.document_relationships.values()
            if doc.get('deduplication_history')
        )

        # Deduplication impact analysis
        total_original_chunks = sum(
            doc.get('chunk_count', 0)
            for doc in self.document_relationships.values()
        ) or total_chunks
        total_consolidated_chunks = total_chunks

        if total_original_chunks > 0:
            stats['deduplication_impact'] = {
                'original_chunks': total_original_chunks,
                'consolidated_chunks': total_consolidated_chunks,
                'consolidation_ratio': (
                    total_consolidated_chunks / total_original_chunks
                    if total_original_chunks else 1.0
                ),
                'space_savings_percentage': (
                    ((total_consolidated_chunks - total_original_chunks) /
                     total_original_chunks) * 100
                    if total_original_chunks else 0.0
                )
            }

        # Recent activity (last 24 hours)
        day_ago = current_time - 86400
        recent_documents = sum(
            1 for creation_time in document_creation_times.values()
            if creation_time > day_ago
        )
        recent_merges = sum(
            1 for merge in self.merge_history_service.merge_history.values()
            if merge.get('timestamp', 0) > day_ago
        )

        stats['recent_activity'] = {
            'documents_created_24h': recent_documents,
            'merges_performed_24h': recent_merges,
            'activity_score': (recent_documents + recent_merges * 2) / 10.0
        }

        return stats

    def find_chunk_content_in_collections(self, chunk_id: str) -> Optional[str]:
        """Find chunk content in memory collections.

        Args:
            chunk_id: The chunk ID to find

        Returns:
            The chunk content if found, None otherwise
        """
        try:
            for collection_name in ['short_term_memory', 'long_term_memory']:
                collection = getattr(self.memory_system, collection_name, None)
                if collection and hasattr(collection, '_collection'):
                    result = collection._collection.get()
                    if result and 'ids' in result and 'documents' in result:
                        for i, (id_val, doc_content) in enumerate(
                            zip(result['ids'], result['documents'])
                        ):
                            if id_val == chunk_id:
                                return doc_content
        except Exception as e:
            logging.debug(f"Error finding chunk content for {chunk_id}: {e}")
        return None

    def cleanup_stale_references(
        self,
        deleted_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Clean up stale chunk and document references.

        Args:
            deleted_ids: Optional list of document/chunk IDs that were deleted

        Returns:
            Cleanup statistics
        """
        stats = {
            'chunks_cleaned': 0,
            'documents_cleaned': 0,
            'orphaned_relationships_cleaned': 0,
            'mode': 'targeted' if deleted_ids else 'full_scan'
        }

        if deleted_ids:
            # Targeted cleanup for specific IDs
            for doc_id in deleted_ids:
                if doc_id in self.document_relationships:
                    del self.document_relationships[doc_id]
                    stats['documents_cleaned'] += 1

                if doc_id in self.chunk_relationships:
                    del self.chunk_relationships[doc_id]
                    stats['chunks_cleaned'] += 1

                chunk_ids_to_remove = [
                    cid for cid in self.chunk_relationships
                    if cid.startswith(doc_id + '_chunk_')
                ]
                for chunk_id in chunk_ids_to_remove:
                    del self.chunk_relationships[chunk_id]
                    stats['chunks_cleaned'] += 1

            logging.info(
                f"Targeted cleanup: removed {stats['documents_cleaned']} documents, "
                f"{stats['chunks_cleaned']} chunks"
            )
        else:
            # Full scan: verify each reference exists in ChromaDB
            valid_chunk_ids = set()

            for collection_name in ['short_term_memory', 'long_term_memory']:
                collection = getattr(self.memory_system, collection_name, None)
                if collection and hasattr(collection, '_collection'):
                    try:
                        result = collection._collection.get()
                        if result and result.get('ids'):
                            valid_chunk_ids.update(result['ids'])
                    except Exception as e:
                        logging.warning(f"Error getting IDs from {collection_name}: {e}")

            orphaned_chunks = [
                cid for cid in list(self.chunk_relationships.keys())
                if cid not in valid_chunk_ids
            ]
            for chunk_id in orphaned_chunks:
                del self.chunk_relationships[chunk_id]
                stats['chunks_cleaned'] += 1

            valid_doc_ids = set()
            for chunk_id in valid_chunk_ids:
                if '_chunk_' in chunk_id:
                    doc_id = chunk_id.rsplit('_chunk_', 1)[0]
                    valid_doc_ids.add(doc_id)
                else:
                    valid_doc_ids.add(chunk_id)

            orphaned_docs = [
                did for did in list(self.document_relationships.keys())
                if did not in valid_doc_ids
            ]
            for doc_id in orphaned_docs:
                del self.document_relationships[doc_id]
                stats['documents_cleaned'] += 1

            for chunk_id, chunk_rel in self.chunk_relationships.items():
                related_chunks = chunk_rel.get('related_chunks', [])
                valid_related = [
                    rel for rel in related_chunks
                    if rel.get('target_chunk_id') in valid_chunk_ids
                ]
                if len(valid_related) < len(related_chunks):
                    removed = len(related_chunks) - len(valid_related)
                    stats['orphaned_relationships_cleaned'] += removed
                    chunk_rel['related_chunks'] = valid_related

            logging.info(
                f"Full scan cleanup: removed {stats['documents_cleaned']} documents, "
                f"{stats['chunks_cleaned']} chunks, "
                f"{stats['orphaned_relationships_cleaned']} orphaned relationships"
            )

        return stats
