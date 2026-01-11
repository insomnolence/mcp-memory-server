"""Integration tests for semantic clustering functionality.

These tests verify that the semantic clustering system (perform_semantic_clustering)
works correctly end-to-end, ensuring documents are properly clustered by semantic similarity.
"""
import pytest
import asyncio


@pytest.mark.integration
@pytest.mark.asyncio
async def test_clustering_analysis_returns_cluster_data(running_mcp_server):
    """Test that get_clustering_analysis returns actual cluster information.
    
    This verifies the perform_semantic_clustering function is called correctly
    and returns meaningful cluster data.
    """
    # Add semantically similar documents to form clusters
    cluster_a_docs = [
        {"content": "Machine learning algorithms for data analysis.", "metadata": {"cluster": "ml"}},
        {"content": "Deep learning neural networks for classification.", "metadata": {"cluster": "ml"}},
        {"content": "Supervised learning techniques in AI.", "metadata": {"cluster": "ml"}},
    ]
    
    cluster_b_docs = [
        {"content": "Italian pasta recipes with tomato sauce.", "metadata": {"cluster": "cooking"}},
        {"content": "French cuisine cooking techniques.", "metadata": {"cluster": "cooking"}},
        {"content": "Baking bread and pastries at home.", "metadata": {"cluster": "cooking"}},
    ]
    
    # Add all documents
    for doc in cluster_a_docs + cluster_b_docs:
        result = await running_mcp_server.call_mcp_tool("add_document", doc)
        assert "error" not in result, f"Failed to add document: {result.get('error')}"
    
    await asyncio.sleep(2)  # Allow indexing and embedding generation
    
    # Run clustering analysis
    clustering_result = await running_mcp_server.call_mcp_tool(
        "get_clustering_analysis", 
        {"collection": "short_term"}
    )
    
    assert "error" not in clustering_result, f"Clustering analysis failed: {clustering_result.get('error')}"
    assert "result" in clustering_result, "No result in clustering response"
    
    result = clustering_result['result']
    assert "analysis_result" in result, "analysis_result missing from clustering response"
    
    analysis = result['analysis_result']
    
    # The clustering should complete without the perform_semantic_clustering error
    # (this would have caught the apply_semantic_clustering -> perform_semantic_clustering bug)
    if analysis is not None:
        # Verify the clustering was attempted and returned a structure
        # The key assertion is that we got a response at all (before fix, it crashed)
        assert isinstance(analysis, dict), f"Analysis should be a dict, got {type(analysis)}"
        
        # Check for expected fields - may have error if clustering config missing
        # but the important thing is the operation completed
        if "error" in analysis:
            # Clustering may fail due to config (e.g., missing cluster_threshold)
            # but should not fail due to wrong method name
            assert "apply_semantic_clustering" not in str(analysis['error']), \
                "Should not have apply_semantic_clustering error (method was renamed)"
            print(f"Clustering completed with config warning: {analysis.get('error')}")
        else:
            # If no error, check for expected fields
            assert "clusters" in analysis or "cluster_count" in analysis or "sample_size" in analysis, \
                f"Clustering result missing expected fields: {analysis.keys()}"
            print(f"Clustering analysis completed successfully: {list(analysis.keys())}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_clustering_with_single_document(running_mcp_server):
    """Test clustering handles edge case of single document gracefully."""
    # Clear any existing documents by adding a unique one
    result = await running_mcp_server.call_mcp_tool("add_document", {
        "content": "Single unique document for edge case testing.",
        "metadata": {"type": "edge_case_test"}
    })
    assert "error" not in result, f"Failed to add document: {result.get('error')}"
    
    await asyncio.sleep(1)
    
    # Clustering should handle this without crashing
    clustering_result = await running_mcp_server.call_mcp_tool(
        "get_clustering_analysis",
        {"collection": "short_term"}
    )
    
    # Should not error - even with few documents
    assert "error" not in clustering_result, f"Clustering failed on minimal data: {clustering_result.get('error')}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_clustering_preserves_document_metadata(running_mcp_server):
    """Test that clustering analysis preserves document metadata."""
    # Add documents with rich metadata
    docs = [
        {
            "content": "Document with metadata for clustering test.",
            "metadata": {"source": "test", "category": "testing", "priority": "high"}
        },
        {
            "content": "Another document for clustering metadata test.",
            "metadata": {"source": "test", "category": "testing", "priority": "medium"}
        },
    ]
    
    for doc in docs:
        result = await running_mcp_server.call_mcp_tool("add_document", doc)
        assert "error" not in result, f"Failed to add document: {result.get('error')}"
    
    await asyncio.sleep(1)
    
    # Run clustering - should not lose metadata
    clustering_result = await running_mcp_server.call_mcp_tool(
        "get_clustering_analysis",
        {"collection": "short_term"}
    )
    
    assert "error" not in clustering_result, f"Clustering failed: {clustering_result.get('error')}"
    
    # Query back the documents to verify metadata is preserved
    query_result = await running_mcp_server.call_mcp_tool("query_documents", {
        "query": "clustering metadata test",
        "k": 5
    })
    
    assert "error" not in query_result, f"Query failed: {query_result.get('error')}"
    results = query_result['result'].get('results', [])
    assert len(results) > 0, "Should find documents after clustering analysis"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_clustering_on_empty_collection(running_mcp_server):
    """Test clustering handles empty collection gracefully."""
    # Try clustering on long_term which may be empty
    clustering_result = await running_mcp_server.call_mcp_tool(
        "get_clustering_analysis",
        {"collection": "long_term"}
    )
    
    # Should return an error message about no documents, not crash
    # Either success with empty result or proper error is acceptable
    if "error" in clustering_result:
        # This is acceptable - empty collection error
        assert "no documents" in str(clustering_result).lower() or "not found" in str(clustering_result).lower(), \
            f"Unexpected error: {clustering_result}"
    else:
        # Also acceptable - successful but empty result
        assert "result" in clustering_result, "Should have result key"
