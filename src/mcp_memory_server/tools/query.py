import logging
from typing import Dict, Any, Optional, List


def query_documents_tool(memory_system, query: str, collections: str = None, k: int = 5, use_reranker: bool = True, reranker_model=None) -> dict:
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
        result = memory_system.query_memories(query, collection_list, k)
        
        # Apply reranking if requested and we have multiple results
        if use_reranker and len(result["content"]) > 1:
            result = apply_reranking(query, result, reranker_model)
        
        return result
    except Exception as e:
        raise Exception(f"Failed to query documents: {str(e)}")


def apply_reranking(query: str, result: dict, reranker_model=None) -> dict:
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
        reranker_scores = reranker_model.predict(query_doc_pairs)
        
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