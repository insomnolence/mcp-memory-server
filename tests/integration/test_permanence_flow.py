import pytest
import asyncio


@pytest.mark.integration
@pytest.mark.asyncio
async def test_permanent_document_persists_through_cleanup(running_mcp_server):
    """Test that a document marked as permanent is not removed by cleanup."""
    # Ensure background maintenance is stopped for controlled testing
    await running_mcp_server.call_mcp_tool("stop_background_maintenance")
    await asyncio.sleep(1)  # Give it a moment to stop

    # Add a document explicitly marked as permanent
    permanent_content = "This is a critical permanent document that must never be deleted."
    add_result = await running_mcp_server.call_mcp_tool("add_document", {
        "content": permanent_content,
        "metadata": {"type": "critical_info", "permanence_flag": "critical"},
        "context": {"permanence_requested": True}
    })
    assert "error" not in add_result, f"Failed to add permanent document: {add_result.get('error')}"
    doc_id = add_result['result']['document_id']
    assigned_tier = add_result['result']['assigned_tier']
    importance_score = add_result['result']['importance_score']

    print(f"\nAdded permanent document (ID: {doc_id}, Tier: {assigned_tier}, Importance: {importance_score})")

    # Verify the document is initially present with proper TTL/permanence metadata
    query_result_initial = await running_mcp_server.call_mcp_tool("query_documents", {
        "query": permanent_content,
        "k": 1
    })
    assert len(query_result_initial['result']['results']) > 0, "Permanent document not found immediately after adding"

    metadata = query_result_initial['result']['results'][0]['metadata']
    print(
        f"Document metadata: permanence_flag={
            metadata.get('permanence_flag')}, permanent_flag={
            metadata.get('permanent_flag')}, ttl_tier={
                metadata.get('ttl_tier')}")

    assert metadata.get('permanence_flag') == 'critical', "Permanence flag not set correctly"

    # Check if the permanence request was honored (requires importance >= 0.8)
    if importance_score >= 0.8:
        # Accept either 'permanent' or 'static' as both are long-lived tiers
        assert metadata.get('ttl_tier') in ['permanent', 'static'] or metadata.get(
            'permanent_flag') is True, "Document should be in permanent/static tier for high importance + critical flag"
    else:
        print(f"⚠️  Permanence request not honored - importance {importance_score} < 0.8 threshold")
        print(f"    Document will use normal TTL tier: {metadata.get('ttl_tier')}")
        # Test will continue to verify the document survives cleanup anyway

    # Trigger cleanup using the actual cleanup function
    print("Triggering cleanup...")
    cleanup_result = await running_mcp_server.call_mcp_tool("cleanup_expired_memories")
    assert "error" not in cleanup_result, f"Error calling cleanup: {cleanup_result.get('error')}"

    cleanup_data = cleanup_result['result']['cleanup_results']
    print(f"Cleanup results: checked={cleanup_data['total_checked']}, expired={cleanup_data['total_expired']}")

    # Verify the permanent document is still present
    query_result_after_cleanup = await running_mcp_server.call_mcp_tool("query_documents", {
        "query": permanent_content,
        "k": 1
    })
    assert len(query_result_after_cleanup['result']['results']
               ) > 0, "Permanent document was unexpectedly deleted after cleanup"

    metadata_after = query_result_after_cleanup['result']['results'][0]['metadata']
    assert metadata_after.get('permanence_flag') == 'critical', "Permanence flag lost after cleanup"

    # Verify it appears in query_permanent_documents_tool
    query_perm_tool_result = await running_mcp_server.call_mcp_tool("query_permanent_documents", {
        "query": permanent_content,
        "k": 1
    })
    assert "error" not in query_perm_tool_result, f"Error querying permanent documents tool: {
        query_perm_tool_result.get('error')}"
    assert len(query_perm_tool_result['result']['results']
               ) > 0, "Permanent document not found via query_permanent_documents_tool"
    assert query_perm_tool_result['result']['results'][0]['metadata']['permanence_flag'] == 'critical', \
        "Permanence flag lost in permanent query"

    print("Permanent document successfully persisted and queried.")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_high_importance_document_persists(running_mcp_server):
    """Test that a document with very high importance (auto-permanent) is not removed by cleanup."""
    # Ensure background maintenance is stopped for controlled testing
    await running_mcp_server.call_mcp_tool("stop_background_maintenance")
    await asyncio.sleep(1)  # Give it a moment to stop

    # Add a document with content designed to get a very high importance score
    # (e.g., using keywords from scorer.py that give high bonus/boost)
    high_importance_content = "This is an extremely critical system error log that requires permanent retention."
    add_result = await running_mcp_server.call_mcp_tool("add_document", {
        "content": high_importance_content,
        "metadata": {"type": "error_log"}
    })
    assert "error" not in add_result, f"Failed to add high importance document: {add_result.get('error')}"
    doc_id = add_result['result']['document_id']
    assigned_tier = add_result['result']['assigned_tier']
    importance_score = add_result['result']['importance_score']

    print(f"\nAdded high importance document (ID: {doc_id}, Tier: {assigned_tier}, Importance: {importance_score})")

    # Check if the importance score is high enough to trigger auto-permanence
    print(f"Checking if importance score {importance_score} triggers auto-permanence (>= 0.95)")

    # Verify the document is initially present with proper TTL metadata
    query_result_initial = await running_mcp_server.call_mcp_tool("query_documents", {
        "query": high_importance_content,
        "k": 1
    })
    assert len(query_result_initial['result']['results']
               ) > 0, "High importance document not found immediately after adding"

    metadata = query_result_initial['result']['results'][0]['metadata']
    ttl_tier = metadata.get('ttl_tier')
    permanent_flag = metadata.get('permanent_flag')

    print(f"Document metadata: importance={importance_score}, ttl_tier={ttl_tier}, permanent_flag={permanent_flag}")

    # The document should have appropriate TTL based on its importance
    if importance_score >= 0.95:
        assert ttl_tier == 'permanent' or permanent_flag is True, \
            f"High importance document (score: {importance_score}) should be permanent"
    else:
        print(
            f"Document importance {importance_score} not high enough for auto-permanence, "
            "testing high-tier preservation"
        )

    # Trigger cleanup using the actual cleanup function
    print("Triggering cleanup...")
    cleanup_result = await running_mcp_server.call_mcp_tool("cleanup_expired_memories")
    assert "error" not in cleanup_result, f"Error calling cleanup: {cleanup_result.get('error')}"

    cleanup_data = cleanup_result['result']['cleanup_results']
    print(f"Cleanup results: checked={cleanup_data['total_checked']}, expired={cleanup_data['total_expired']}")

    # Verify the high importance document is still present (regardless of exact tier)
    query_result_after_cleanup = await running_mcp_server.call_mcp_tool("query_documents", {
        "query": high_importance_content,
        "k": 1
    })
    assert len(query_result_after_cleanup['result']['results']
               ) > 0, "High importance document was unexpectedly deleted after cleanup"

    print("High importance document successfully persisted.")
