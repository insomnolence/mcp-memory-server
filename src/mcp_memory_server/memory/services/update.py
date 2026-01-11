"""
Document Update Service

Handles CRUD operations for documents including:
- Document deletion
- Importance score updates
- Content updates (delete + re-add)
"""

import time
import logging
from typing import Dict, Any, Optional

from langchain_chroma import Chroma


class DocumentUpdateService:
    """Service responsible for document CRUD operations."""

    def __init__(
        self,
        short_term_memory: Chroma,
        long_term_memory: Chroma,
        chunk_manager,
        lifecycle_manager=None,
        storage_service=None
    ):
        """Initialize update service.

        Args:
            short_term_memory: Chroma collection for short-term storage
            long_term_memory: Chroma collection for long-term storage
            chunk_manager: ChunkRelationshipManager instance
            lifecycle_manager: Optional LifecycleManager instance
            storage_service: MemoryStorageService instance for add_memory
        """
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.chunk_manager = chunk_manager
        self.lifecycle_manager = lifecycle_manager
        self.storage_service = storage_service

    def set_lifecycle_manager(self, lifecycle_manager):
        """Set the lifecycle manager for TTL recalculation."""
        self.lifecycle_manager = lifecycle_manager

    def set_storage_service(self, storage_service):
        """Set the storage service for add_memory calls."""
        self.storage_service = storage_service

    def _get_collection(self, collection_name: str) -> Optional[Chroma]:
        """Get collection by name."""
        if collection_name == "short_term":
            return self.short_term_memory
        elif collection_name == "long_term":
            return self.long_term_memory
        return None

    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document and all its chunks by document_id.

        Args:
            document_id: The document ID to delete (memory_id or document_id)

        Returns:
            Dictionary with deletion results including chunks removed and collection
        """
        result = {
            "success": False,
            "document_id": document_id,
            "chunks_deleted": 0,
            "collection": None,
            "message": ""
        }

        # Search both collections for the document
        for collection_name in ["short_term", "long_term"]:
            collection = self._get_collection(collection_name)

            try:
                if hasattr(collection, '_collection'):
                    # Get all documents and filter by document_id
                    all_docs = collection._collection.get()

                    ids_to_delete = []
                    for i, metadata in enumerate(all_docs.get('metadatas', [])):
                        if metadata:
                            doc_id = metadata.get('document_id') or metadata.get('memory_id')
                            if doc_id == document_id:
                                ids_to_delete.append(all_docs['ids'][i])

                    if ids_to_delete:
                        collection._collection.delete(ids=ids_to_delete)

                        # Clean up chunk relationships if available
                        if self.chunk_manager:
                            try:
                                if document_id in self.chunk_manager.document_relationships:
                                    del self.chunk_manager.document_relationships[document_id]
                                # Clean up chunk relationships
                                for chunk_id in ids_to_delete:
                                    if chunk_id in self.chunk_manager.chunk_relationships:
                                        del self.chunk_manager.chunk_relationships[chunk_id]
                            except Exception as rel_error:
                                logging.warning(f"Error cleaning up relationships: {rel_error}")

                        result["success"] = True
                        result["chunks_deleted"] = len(ids_to_delete)
                        result["collection"] = collection_name
                        result["message"] = f"Deleted {len(ids_to_delete)} chunks from {collection_name}"

                        logging.info(
                            f"Deleted document {document_id}: "
                            f"{len(ids_to_delete)} chunks from {collection_name}"
                        )
                        return result

            except Exception as e:
                logging.error(f"Error searching {collection_name} for document {document_id}: {e}")

        result["message"] = f"Document {document_id} not found in any collection"
        return result

    async def update_document_importance(
        self,
        document_id: str,
        new_importance: float,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a document's importance score and recalculate TTL.

        Args:
            document_id: The document ID to update
            new_importance: New importance score (0.0-1.0, should be < 0.95 for non-permanent)
            reason: Optional reason for the importance change

        Returns:
            Dictionary with update results including old/new scores and TTL tier
        """
        result = {
            "success": False,
            "document_id": document_id,
            "old_importance": None,
            "new_importance": new_importance,
            "old_ttl_tier": None,
            "new_ttl_tier": None,
            "chunks_updated": 0,
            "collection": None,
            "message": ""
        }

        # Validate importance score
        if not (0.0 <= new_importance <= 1.0):
            result["message"] = "Importance score must be between 0.0 and 1.0"
            return result

        # Search both collections for the document
        for collection_name in ["short_term", "long_term"]:
            collection = self._get_collection(collection_name)

            try:
                if hasattr(collection, '_collection'):
                    all_docs = collection._collection.get()

                    ids_to_update = []
                    old_metadata_list = []

                    for i, metadata in enumerate(all_docs.get('metadatas', [])):
                        if metadata:
                            doc_id = metadata.get('document_id') or metadata.get('memory_id')
                            if doc_id == document_id:
                                ids_to_update.append(all_docs['ids'][i])
                                old_metadata_list.append(metadata.copy())

                    if ids_to_update:
                        # Store old values from first chunk
                        result["old_importance"] = old_metadata_list[0].get('importance_score')
                        result["old_ttl_tier"] = old_metadata_list[0].get('ttl_tier')

                        # Prepare updated metadata for each chunk
                        new_metadatas = []
                        for old_meta in old_metadata_list:
                            updated_meta = old_meta.copy()
                            updated_meta['importance_score'] = new_importance

                            # Add demotion reason if provided
                            if reason:
                                updated_meta['importance_change_reason'] = reason
                            updated_meta['importance_changed_at'] = time.time()

                            # Recalculate TTL if lifecycle manager is available
                            if self.lifecycle_manager and hasattr(self.lifecycle_manager, 'ttl_manager'):
                                updated_meta = self.lifecycle_manager.ttl_manager.add_ttl_metadata(
                                    updated_meta, new_importance
                                )

                            new_metadatas.append(updated_meta)

                        # Update in ChromaDB
                        collection._collection.update(
                            ids=ids_to_update,
                            metadatas=new_metadatas
                        )

                        result["success"] = True
                        result["new_ttl_tier"] = new_metadatas[0].get('ttl_tier')
                        result["chunks_updated"] = len(ids_to_update)
                        result["collection"] = collection_name

                        old_imp = result['old_importance']
                        old_tier = result['old_ttl_tier']
                        new_tier = result['new_ttl_tier']
                        result["message"] = (
                            f"Updated {len(ids_to_update)} chunks: "
                            f"importance {old_imp:.2f if old_imp else 0:.2f} -> {new_importance:.2f}, "
                            f"TTL tier {old_tier} -> {new_tier}"
                        )

                        logging.info(f"Updated document {document_id} importance: {result['message']}")
                        return result

            except Exception as e:
                logging.error(f"Error updating {collection_name} document {document_id}: {e}")
                result["message"] = f"Error updating document: {str(e)}"
                return result  # Return immediately on error

        if not result["success"] and not result["message"]:
            result["message"] = f"Document {document_id} not found in any collection"
        return result

    async def update_document_metadata(
        self,
        chunk_id: str,
        metadata_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update specific metadata fields on a chunk.

        This method updates arbitrary metadata fields on a single chunk,
        merging the new values with existing metadata. Used primarily for
        persisting relationship data to ChromaDB.

        Args:
            chunk_id: The chunk_id (metadata field) to update
            metadata_updates: Dictionary of metadata fields to update/add

        Returns:
            Dictionary with update results including success status
        """
        result = {
            "success": False,
            "chunk_id": chunk_id,
            "fields_updated": [],
            "collection": None,
            "message": ""
        }

        if not chunk_id or not isinstance(chunk_id, str):
            result["message"] = "chunk_id must be a non-empty string"
            return result

        if not metadata_updates or not isinstance(metadata_updates, dict):
            result["message"] = "metadata_updates must be a non-empty dictionary"
            return result

        # Search both collections for the chunk
        for collection_name in ["short_term", "long_term"]:
            collection = self._get_collection(collection_name)

            try:
                if hasattr(collection, '_collection'):
                    # Query by chunk_id metadata field
                    query_result = collection._collection.get(
                        where={'chunk_id': chunk_id}
                    )

                    if query_result and query_result.get('ids') and len(query_result['ids']) > 0:
                        chromadb_id = query_result['ids'][0]
                        existing_metadata = query_result['metadatas'][0] if query_result.get('metadatas') else {}

                        # Merge existing metadata with updates
                        updated_metadata = existing_metadata.copy()
                        updated_metadata.update(metadata_updates)
                        updated_metadata['metadata_updated_at'] = time.time()

                        # Update in ChromaDB
                        collection._collection.update(
                            ids=[chromadb_id],
                            metadatas=[updated_metadata]
                        )

                        result["success"] = True
                        result["fields_updated"] = list(metadata_updates.keys())
                        result["collection"] = collection_name
                        result["message"] = f"Updated {len(metadata_updates)} metadata fields on chunk {chunk_id}"

                        logging.debug(f"Updated metadata for chunk {chunk_id}: {list(metadata_updates.keys())}")
                        return result

            except Exception as e:
                logging.error(f"Error updating metadata for chunk {chunk_id} in {collection_name}: {e}")
                result["message"] = f"Error updating metadata: {str(e)}"
                return result

        result["message"] = f"Chunk {chunk_id} not found in any collection"
        return result

    async def update_document_content(
        self,
        document_id: str,
        new_content: str,
        new_metadata: Optional[Dict[str, Any]] = None,
        preserve_importance: bool = True
    ) -> Dict[str, Any]:
        """Update a document's content by replacing it.

        This performs a delete-and-add operation to update document content,
        optionally preserving the original importance score and metadata.

        Args:
            document_id: The document ID to update
            new_content: The new content for the document
            new_metadata: Optional new metadata (merged with existing if not provided)
            preserve_importance: If True, preserve the original importance score

        Returns:
            Dictionary with update results
        """
        result = {
            "success": False,
            "document_id": document_id,
            "old_chunks": 0,
            "new_chunks": 0,
            "collection": None,
            "importance_preserved": False,
            "message": ""
        }

        if not new_content or not isinstance(new_content, str):
            result["message"] = "New content must be a non-empty string"
            return result

        if not document_id or not isinstance(document_id, str):
            result["message"] = "Document ID must be a non-empty string"
            return result

        if not self.storage_service:
            result["message"] = "Storage service not configured"
            return result

        # First, find the existing document and its metadata
        existing_doc = None
        existing_metadata = None
        source_collection = None

        for collection_name in ["short_term", "long_term"]:
            collection = self._get_collection(collection_name)
            try:
                if hasattr(collection, '_collection'):
                    all_docs = collection._collection.get()
                    for i, metadata in enumerate(all_docs.get('metadatas', [])):
                        if metadata:
                            doc_id = metadata.get('document_id') or metadata.get('memory_id')
                            if doc_id == document_id:
                                existing_doc = {
                                    'id': all_docs['ids'][i],
                                    'content': all_docs.get('documents', [None])[i],
                                    'metadata': metadata
                                }
                                existing_metadata = metadata.copy()
                                source_collection = collection_name
                                break
                if existing_doc:
                    break
            except Exception as e:
                logging.error(f"Error searching {collection_name} for {document_id}: {e}")

        if not existing_doc:
            result["message"] = f"Document {document_id} not found in any collection"
            return result

        # Delete the existing document
        delete_result = await self.delete_document(document_id)
        if not delete_result.get("success"):
            result["message"] = f"Failed to delete existing document: {delete_result.get('message')}"
            return result

        result["old_chunks"] = delete_result.get("chunks_deleted", 0)

        # Prepare metadata for the new document
        final_metadata = existing_metadata.copy() if existing_metadata else {}

        # Update with new metadata if provided
        if new_metadata:
            final_metadata.update(new_metadata)

        # Mark as updated
        final_metadata['updated_at'] = time.time()
        final_metadata['update_count'] = final_metadata.get('update_count', 0) + 1

        # Prepare context for add_memory
        context = {}
        if preserve_importance and existing_metadata:
            old_importance = existing_metadata.get('importance_score')
            if old_importance is not None:
                context['preserved_importance'] = old_importance
                result["importance_preserved"] = True

        # Add the document with new content
        try:
            add_result = await self.storage_service.add_memory(
                content=new_content,
                metadata=final_metadata,
                context=context
            )

            if add_result.get("success") or add_result.get("memory_id"):
                result["success"] = True
                result["new_chunks"] = add_result.get("chunks_added", 0)
                result["collection"] = add_result.get("collection", source_collection)
                result["new_document_id"] = add_result.get("memory_id", document_id)
                result["message"] = (
                    f"Document updated successfully: {result['old_chunks']} old chunks removed, "
                    f"{result['new_chunks']} new chunks added"
                )
                logging.info(f"Updated document {document_id}: {result['message']}")
            else:
                result["message"] = f"Failed to add updated document: {add_result.get('message')}"
                logging.error(f"Failed to update document {document_id}: {result['message']}")

        except Exception as e:
            result["message"] = f"Error adding updated document: {str(e)}"
            logging.error(f"Error updating document {document_id}: {e}")

        return result
