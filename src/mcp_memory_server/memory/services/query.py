"""
Memory Query Service

Handles search and retrieval operations including:
- Query execution across collections
- Result scoring and ranking
- Access statistics updates
- Related chunk retrieval
"""

import time
import logging
import asyncio
from typing import Dict, Any, List, Optional

from langchain_chroma import Chroma

# Import ChromaDB errors for specific exception handling
try:
    from chromadb.errors import ChromaError
except ImportError:
    ChromaError = Exception


class MemoryQueryService:
    """Service responsible for search and retrieval operations."""

    def __init__(
        self,
        short_term_memory: Chroma,
        long_term_memory: Chroma,
        routing_service,
        importance_scorer,
        chunk_manager,
        query_monitor,
        deduplicator,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize query service.

        Args:
            short_term_memory: Chroma collection for short-term storage
            long_term_memory: Chroma collection for long-term storage
            routing_service: QueryRoutingService instance
            importance_scorer: MemoryImportanceScorer instance
            chunk_manager: ChunkRelationshipManager instance
            query_monitor: QueryPerformanceMonitor instance
            deduplicator: MemoryDeduplicator instance
            config: Configuration dictionary
        """
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.routing_service = routing_service
        self.importance_scorer = importance_scorer
        self.chunk_manager = chunk_manager
        self.query_monitor = query_monitor
        self.deduplicator = deduplicator
        self.config = config or {}

    def _get_collection(self, collection_name: str) -> Optional[Chroma]:
        """Get collection by name."""
        if collection_name == "short_term":
            return self.short_term_memory
        elif collection_name == "long_term":
            return self.long_term_memory
        return None

    async def query_memories(
        self,
        query: str,
        collections: Optional[List[str]] = None,
        k: int = 5,
        use_smart_routing: bool = True
    ) -> Dict[str, Any]:
        """Query across memory collections with deduplication-aware intelligent routing.

        Args:
            query: Search query string
            collections: List of collection names to search (default: smart routing)
            k: Maximum number of results to return
            use_smart_routing: Whether to use deduplication-aware smart routing

        Returns:
            Dictionary containing formatted search results
        """
        # Start performance tracking
        start_time = time.time()
        current_time = start_time

        # Use smart routing if enabled and collections not explicitly specified
        if use_smart_routing and collections is None:
            collections, collection_limits, effective_k = self.routing_service.smart_query_routing(query, k)
        else:
            if collections is None:
                collections = ["short_term", "long_term"]
            collection_limits = [k // len(collections)] * len(collections)
            effective_k = k

        all_results = []

        # Query each collection with smart limits
        for i, collection_name in enumerate(collections):
            collection = self._get_collection(collection_name)
            if collection is None:
                continue

            # Use collection-specific limits from smart routing
            collection_k = collection_limits[i] if i < len(collection_limits) else effective_k
            search_k = max(collection_k * 2, 10)  # Get extra candidates for better ranking

            try:
                initial_docs = await asyncio.to_thread(collection.similarity_search_with_score, query, k=search_k)

                for doc, distance in initial_docs:
                    memory_data = {
                        'document': doc.page_content,
                        'metadata': doc.metadata,
                        'distance': distance,
                        'collection': collection_name
                    }

                    # Enhanced retrieval score with deduplication awareness
                    retrieval_score = await self._calculate_enhanced_retrieval_score(
                        memory_data, query, current_time
                    )
                    memory_data['retrieval_score'] = retrieval_score

                    all_results.append(memory_data)

            except ChromaError as e:
                logging.warning(f"ChromaDB error querying {collection_name}: {e}")
                continue
            except Exception as e:
                logging.warning(f"Unexpected error querying {collection_name}: {e}")
                continue

        # Sort by retrieval score and take top k
        all_results.sort(key=lambda x: x['retrieval_score'], reverse=True)
        top_results = all_results[:effective_k]

        # Update access statistics for retrieved memories
        self._update_access_stats(top_results)

        # Format for MCP response with enhanced metadata and related chunks
        content_blocks = []
        related_chunks_included = 0

        for result in top_results:
            # Add deduplication information if available
            dedup_info = ""
            if result['metadata'].get('duplicate_sources'):
                dedup_info = f" | Merged from {len(result['metadata']['duplicate_sources'])} sources"

            # Get related chunks for better context
            related_chunks = []
            chunk_id = result['metadata'].get('chunk_id')
            if chunk_id and self.chunk_manager:
                try:
                    related_chunks = await asyncio.to_thread(
                        self.chunk_manager.retrieve_related_chunks, chunk_id, k_related=2
                    )
                    if related_chunks:
                        related_chunks_included += len(related_chunks)
                except Exception as e:
                    logging.warning(f"Failed to retrieve related chunks for {chunk_id}: {e}")

            # Format main result
            score = result['retrieval_score']
            coll = result['collection']
            doc = result['document']
            result_text = f"**Score: {score:.3f} | Collection: {coll}{dedup_info}**\n\n{doc}\n\n"

            # Add related chunks context if available
            if related_chunks:
                result_text += "**Related Context:**\n"
                for related in related_chunks[:2]:  # Limit to 2 most relevant
                    relation_type = related.get('relationship_type', 'related')
                    relevance = related.get('context_relevance', 0.0)

                    result_text += f"*{relation_type.replace('_', ' ').title()} (relevance: {relevance:.2f}):*\n"
                    result_text += f"{related.get('content_preview', 'No preview available')}\n\n"

            result_text += f"**Metadata:** {result['metadata']}"

            content_blocks.append({
                "type": "text",
                "text": result_text,
                "metadata": result['metadata']  # Include metadata as separate field for MCP compatibility
            })

        # Calculate processing time and create results
        processing_time = time.time() - start_time

        results = {
            "content": content_blocks,
            "total_results": len(all_results),
            "collections_searched": collections,
            "smart_routing_used": use_smart_routing and collections != ["short_term", "long_term"],
            "query_optimization_applied": use_smart_routing,
            "processing_time_ms": processing_time * 1000,
            "related_chunks_included": related_chunks_included,
            "context_enhancement_enabled": self.chunk_manager is not None
        }

        # Track query performance
        try:
            query_metadata = {
                'effective_k': effective_k,
                'original_k': k,
                'collection_limits': collection_limits
            }
            self.query_monitor.track_query(query, results, processing_time, query_metadata)
        except Exception as e:
            logging.warning(f"Failed to track query performance: {e}")

        return results

    async def _calculate_enhanced_retrieval_score(
        self,
        memory_data: Dict[str, Any],
        query: str,
        current_time: float
    ) -> float:
        """Calculate retrieval score with deduplication awareness.

        Args:
            memory_data: Memory data dictionary with document and metadata
            query: The search query
            current_time: Current timestamp

        Returns:
            Enhanced retrieval score
        """
        metadata = memory_data['metadata']
        distance = memory_data['distance']

        # Calculate base retrieval score (offload to thread)
        # Pass the full memory_data dict as expected by calculate_retrieval_score
        base_score = await asyncio.to_thread(
            self.importance_scorer.calculate_retrieval_score,
            memory_data,
            query,
            current_time
        )

        # Apply deduplication quality boost
        dedup_boost = 0.0
        if metadata.get('duplicate_merged'):
            # This document represents merged knowledge from multiple sources
            source_count = len(metadata.get('duplicate_sources', []))
            if source_count > 1:
                # Boost by log of source count (diminishing returns)
                import math
                dedup_boost = 0.05 * math.log(source_count + 1)

        # Apply recency boost for recently accessed content
        recency_boost = 0.0
        last_accessed = metadata.get('last_accessed', 0)
        if last_accessed > 0:
            hours_since_access = (current_time - last_accessed) / 3600
            if hours_since_access < 24:
                recency_boost = 0.05 * (1 - hours_since_access / 24)

        return min(base_score + dedup_boost + recency_boost, 1.0)

    def _update_access_stats(self, results: List[Dict[str, Any]]) -> None:
        """Update access statistics for retrieved memories.

        Args:
            results: List of search result dictionaries
        """
        current_time = time.time()

        for result in results:
            try:
                metadata = result['metadata']
                chunk_id = metadata.get('chunk_id')
                collection_name = result['collection']

                if chunk_id:
                    _ = self._get_collection(collection_name)  # noqa: F841

                    # Update metadata (this is a simplified approach)
                    # In production, you'd want a more efficient update mechanism
                    new_access_count = metadata.get('access_count', 0) + 1
                    metadata['access_count'] = new_access_count
                    metadata['last_accessed'] = current_time

            except Exception as e:
                logging.warning(f"Error updating access stats: {e}")
