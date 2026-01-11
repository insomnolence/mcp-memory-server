import logging
from ..server.errors import create_tool_error, MCPErrorCode


async def query_documents_tool(memory_system, query: str, collections: str = None,
                               k: int = 5, use_reranker: bool = True, reranker_model=None) -> dict:
    """Query documents from the hierarchical memory system with intelligent scoring.

    Args:
        memory_system: Instance of HierarchicalMemorySystem
        query: Search query string
        collections: Comma-separated collection names to search
        k: Maximum number of results to return
        use_reranker: Whether to apply cross-encoder reranking
        reranker_model: Cross-encoder model for reranking (optional)

    Returns:
        Dictionary containing formatted search results
    """
    try:
        # Validate inputs
        if not query or not isinstance(query, str):
            return create_tool_error(
                "Query must be a non-empty string",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={"field": "query", "provided_type": type(query).__name__}
            )

        if k is not None and (not isinstance(k, int) or k < 1):
            return create_tool_error(
                "Parameter 'k' must be a positive integer",
                MCPErrorCode.VALIDATION_ERROR,
                additional_data={"field": "k", "provided_value": k, "expected": "positive integer"}
            )

        # Parse collections parameter
        collection_list = None
        if collections:
            if isinstance(collections, str):
                collection_list = [c.strip() for c in collections.split(",")]
            elif isinstance(collections, list):
                collection_list = collections
            else:
                return create_tool_error(
                    "Collections must be a string (comma-separated) or list of collection names",
                    MCPErrorCode.VALIDATION_ERROR,
                    additional_data={"field": "collections", "provided_type": type(collections).__name__}
                )

        # Query using hierarchical memory system
        result = await memory_system.query_memories(query, collection_list, k)

        # Log query execution details
        logging.info(
            f"Query executed: query='{query[:50]}...' collections={collection_list} k={k} "
            f"found={len(result.get('content', []))} results"
        )

        # Apply reranking if requested and we have multiple results
        if use_reranker and len(result["content"]) > 1:
            result = await apply_reranking(query, result, reranker_model)

        # Transform to MCP-compliant format (2025-06-18 spec)
        # Return the full formatted text blocks directly
        mcp_result = {
            "content": [],
            "isError": False  # Required by MCP spec
        }

        for content_block in result.get("content", []):
            # Use the full formatted text directly
            text = content_block.get("text", "")
            if text.strip():
                mcp_result["content"].append({
                    "type": "text",
                    "text": text
                })

        # Add additional metadata from the original result
        mcp_result.update({
            "total_results": result.get("total_results", len(mcp_result["content"])),
            "collections_searched": result.get("collections_searched", []),
            "processing_time_ms": result.get("processing_time_ms", 0),
            "smart_routing_used": result.get("smart_routing_used", False)
        })

        # Log final result summary with sample content
        logging.info(
            f"Query complete: returning {len(mcp_result['content'])} content blocks "
            f"(total_results={mcp_result['total_results']})"
        )
        if mcp_result['content']:
            sample_text = mcp_result['content'][0].get('text', '')[:100]
            logging.info(f"Sample content: {sample_text}...")

        return mcp_result
    except Exception as e:
        return create_tool_error(
            f"Failed to query documents: {str(e)}",
            MCPErrorCode.MEMORY_SYSTEM_ERROR,
            original_error=e
        )


async def apply_reranking(query: str, result: dict, reranker_model=None) -> dict:
    """Apply cross-encoder reranking to improve result quality.

    Args:
        query: Search query string
        result: Search results dictionary
        reranker_model: Cross-encoder model for reranking

    Returns:
        Reranked search results dictionary
    """
    try:
        if reranker_model is None:
            logging.warning("No reranker model provided, skipping reranking")
            return result

        content_blocks = result["content"]
        if len(content_blocks) <= 1:
            return result

        # Extract text content for reranking
        doc_texts = []
        for block in content_blocks:
            # Extract the main content (skip the score/metadata lines)
            text_lines = block["text"].split('\n')
            content_start = 0
            for i, line in enumerate(text_lines):
                if line.startswith('**Score:') or line.startswith('**Relevance:'):
                    content_start = i + 2  # Skip score line and empty line
                    break
            content = '\n'.join(text_lines[content_start:])
            # Remove metadata section
            if '**Metadata:**' in content:
                content = content.split('**Metadata:**')[0].strip()
            doc_texts.append(content)

        # Apply reranking
        query_doc_pairs = [(query, doc_text) for doc_text in doc_texts]
        import asyncio
        reranker_scores = await asyncio.to_thread(reranker_model.predict, query_doc_pairs)

        # Combine with original scores and reorder
        scored_blocks = list(zip(content_blocks, reranker_scores))
        scored_blocks.sort(key=lambda x: x[1], reverse=True)

        # Update content blocks with reranker scores
        reranked_content = []
        for block, rerank_score in scored_blocks:
            # Update the score display to include reranker score
            text = block["text"]
            if text.startswith('**Score:'):
                # Replace the score line to include reranker score
                lines = text.split('\n')
                lines[0] = f"**Score: {
                    rerank_score:.3f} (reranked) | {
                    lines[0].split(
                        '|', 1)[1] if '|' in lines[0] else ''}**"
                text = '\n'.join(lines)

            reranked_content.append({
                "type": "text",
                "text": text
            })

        result["content"] = reranked_content
        result["reranked"] = True
        return result

    except Exception as e:
        logging.warning(f"Reranking failed: {e}")
        return result
