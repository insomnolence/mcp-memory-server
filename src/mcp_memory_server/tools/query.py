import logging
from typing import Dict, Any, Optional, List


async def query_documents_tool(memory_system, query: str, collections: str = None, k: int = 5, use_reranker: bool = True, reranker_model=None) -> dict:
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
        # Parse collections parameter
        if collections:
            collection_list = [c.strip() for c in collections.split(",")]
        else:
            collection_list = None
        
        # Query using hierarchical memory system
        result = await memory_system.query_memories(query, collection_list, k)
        
        # Apply reranking if requested and we have multiple results
        if use_reranker and len(result["content"]) > 1:
            result = await apply_reranking(query, result, reranker_model)
        
        # Transform to MCP-compliant format
        mcp_result = {
            "results": []
        }
        
        for content_block in result.get("content", []):
            # Extract content from the formatted text blocks
            text = content_block.get("text", "")
            
            # Extract the actual content (skip score and metadata)
            content_lines = text.split('\n')
            actual_content = ""
            in_content = False
            
            for line in content_lines:
                if line.startswith('**Score:'):
                    continue
                elif line.startswith('**Related Context:**'):
                    break  # Stop at related context for now
                elif line.startswith('**Metadata:**'):
                    break  # Stop at metadata
                elif line.strip() == "":
                    if in_content:
                        actual_content += "\n"
                else:
                    in_content = True
                    if actual_content:
                        actual_content += "\n"
                    actual_content += line
            
            if actual_content.strip():
                mcp_result["results"].append({
                    "content": actual_content.strip(),
                    "metadata": content_block.get("metadata", {})
                })
        
        # Add additional metadata from the original result
        mcp_result.update({
            "total_results": result.get("total_results", len(mcp_result["results"])),
            "collections_searched": result.get("collections_searched", []),
            "processing_time_ms": result.get("processing_time_ms", 0),
            "smart_routing_used": result.get("smart_routing_used", False)
        })
        
        return mcp_result
    except Exception as e:
        raise Exception(f"Failed to query documents: {str(e)}")


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
                lines[0] = f"**Score: {rerank_score:.3f} (reranked) | {lines[0].split('|', 1)[1] if '|' in lines[0] else ''}**"
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