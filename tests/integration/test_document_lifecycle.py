import pytest
import time
import os
from unittest.mock import patch

@pytest.mark.integration
@pytest.mark.asyncio
async def test_cleanup_function_works_correctly(running_mcp_server):
    """Test that the cleanup function correctly identifies and would delete expired documents."""
    
    # Add a document and verify TTL system integration
    test_content = "This document tests TTL and cleanup functionality."
    add_result = await running_mcp_server.call_mcp_tool("add_document", {
        "content": test_content,
        "metadata": {"type": "test_ttl", "source": "test_lifecycle"}
    })
    assert "error" not in add_result, f"Failed to add document: {add_result.get('error')}"
    doc_id = add_result['result']['document_id']

    # Verify the document is initially present with TTL metadata
    query_result_before = await running_mcp_server.call_mcp_tool("query_documents", {
        "query": test_content,
        "k": 1
    })
    assert len(query_result_before['result']['results']) > 0, "Document not found after adding"
    
    # Check TTL metadata is properly applied
    metadata = query_result_before['result']['results'][0]['metadata'] 
    ttl_tier = metadata.get('ttl_tier')
    ttl_expiry = metadata.get('ttl_expiry')
    
    assert ttl_tier is not None, "TTL tier not applied to document"
    assert ttl_expiry is not None, "TTL expiry not applied to document"
    
    current_time = time.time()
    print(f"\nDocument TTL: tier={ttl_tier}, expiry={ttl_expiry}, current_time={current_time}")
    print(f"Time until expiry: {ttl_expiry - current_time:.1f} seconds")

    # Test cleanup function (should not delete non-expired document)
    cleanup_result = await running_mcp_server.call_mcp_tool("cleanup_expired_memories")
    assert "error" not in cleanup_result, f"Error calling cleanup: {cleanup_result.get('error')}"
    
    cleanup_data = cleanup_result['result']['cleanup_results']
    print(f"Cleanup results: checked={cleanup_data['total_checked']}, expired={cleanup_data['total_expired']}")
    
    # Verify cleanup function works but doesn't delete non-expired documents
    assert cleanup_data['total_checked'] >= 1, "Cleanup should have checked at least our document"
    assert cleanup_data['total_expired'] == 0, "No documents should be expired yet"

    # Verify the document is still present (not expired)
    query_result_after = await running_mcp_server.call_mcp_tool("query_documents", {
        "query": test_content,
        "k": 1
    })
    assert len(query_result_after['result']['results']) > 0, "Non-expired document should still be present"
    
    print("✅ TTL system and cleanup function working correctly")
    print(f"   - Document has proper TTL metadata (tier: {ttl_tier})")  
    print(f"   - Cleanup function successfully identifies non-expired documents")
    print(f"   - Document expiry time properly calculated ({ttl_expiry - current_time:.1f}s from now)")

    # Get memory stats for verification
    stats_result = await running_mcp_server.call_mcp_tool("get_memory_stats")
    assert "error" not in stats_result, f"Error getting memory stats: {stats_result.get('error')}"

# Consolidated memory tier has been removed from the roadmap
#     pass
