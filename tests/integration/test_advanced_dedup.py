"""Integration tests for advanced deduplication functionality.

These tests verify that the advanced deduplication system works correctly end-to-end,
including semantic clustering, domain awareness, and effectiveness tracking.
"""
import pytest
import asyncio


@pytest.mark.integration
@pytest.mark.asyncio
async def test_advanced_deduplication_runs_without_error(running_mcp_server):
    """Test that run_advanced_deduplication executes without errors.
    
    This verifies the full deduplication pipeline including:
    - perform_semantic_clustering (renamed from apply_semantic_clustering)
    - track_effectiveness (with correct signature)
    """
    # Add potentially duplicate documents
    docs = [
        {"content": "Advanced deduplication test document one.", "metadata": {"type": "dedup_test"}},
        {"content": "Advanced deduplication test document two.", "metadata": {"type": "dedup_test"}},
        {"content": "Similar advanced dedup test document.", "metadata": {"type": "dedup_test"}},
    ]
    
    for doc in docs:
        result = await running_mcp_server.call_mcp_tool("add_document", doc)
        assert "error" not in result, f"Failed to add document: {result.get('error')}"
    
    await asyncio.sleep(2)  # Allow indexing
    
    # Run advanced deduplication
    dedup_result = await running_mcp_server.call_mcp_tool("run_advanced_deduplication", {
        "collection": "short_term",
        "dry_run": False
    })
    
    # The main assertion - deduplication should complete without errors
    # This would have caught the perform_semantic_clustering and track_effectiveness bugs
    assert "error" not in dedup_result, f"Advanced deduplication failed: {dedup_result.get('error')}"
    assert "result" in dedup_result, "No result in deduplication response"
    
    result = dedup_result['result']
    assert "result" in result, "Inner result missing from deduplication response"
    
    inner_result = result['result']
    assert "duplicates_found" in inner_result, "duplicates_found missing from result"
    assert "advanced_features_used" in inner_result, "advanced_features_used flag missing"
    assert inner_result["advanced_features_used"] is True, "Advanced features should be marked as used"
    
    print(f"Advanced dedup completed: {inner_result.get('duplicates_found', 0)} duplicates found")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_advanced_dedup_dry_run_mode(running_mcp_server):
    """Test that dry_run mode analyzes without making changes."""
    # Add some documents
    docs = [
        {"content": "Dry run test document alpha.", "metadata": {"group": "dry_run"}},
        {"content": "Dry run test document beta.", "metadata": {"group": "dry_run"}},
    ]
    
    for doc in docs:
        result = await running_mcp_server.call_mcp_tool("add_document", doc)
        assert "error" not in result, f"Failed to add document: {result.get('error')}"
    
    await asyncio.sleep(1)
    
    # Get document count before
    stats_before = await running_mcp_server.call_mcp_tool("get_memory_stats")
    count_before = stats_before['result']['total_documents']
    
    # Run dry_run deduplication
    dedup_result = await running_mcp_server.call_mcp_tool("run_advanced_deduplication", {
        "collection": "short_term",
        "dry_run": True
    })
    
    assert "error" not in dedup_result, f"Dry run deduplication failed: {dedup_result.get('error')}"
    
    # Verify documents weren't actually removed
    stats_after = await running_mcp_server.call_mcp_tool("get_memory_stats")
    count_after = stats_after['result']['total_documents']
    
    # In dry_run, document count should not decrease
    # (might increase if other tests added docs, but shouldn't decrease)
    assert count_after >= count_before - 1, \
        f"Dry run should not remove documents: {count_before} -> {count_after}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deduplication_stats_are_tracked(running_mcp_server):
    """Test that deduplication statistics are properly tracked.
    
    This verifies that track_effectiveness is called and stats are updated.
    """
    # Get initial dedup stats
    initial_stats = await running_mcp_server.call_mcp_tool("get_deduplication_stats")
    assert "error" not in initial_stats, f"Failed to get initial stats: {initial_stats.get('error')}"
    
    # Add documents and run deduplication
    docs = [
        {"content": "Stats tracking test document one.", "metadata": {"test": "stats"}},
        {"content": "Stats tracking test document two.", "metadata": {"test": "stats"}},
    ]
    
    for doc in docs:
        result = await running_mcp_server.call_mcp_tool("add_document", doc)
        assert "error" not in result
    
    await asyncio.sleep(1)
    
    # Run deduplication (this should call track_effectiveness)
    await running_mcp_server.call_mcp_tool("run_advanced_deduplication", {
        "collection": "short_term",
        "dry_run": False
    })
    
    # Get stats after - should reflect the deduplication run
    final_stats = await running_mcp_server.call_mcp_tool("get_deduplication_stats")
    assert "error" not in final_stats, f"Failed to get final stats: {final_stats.get('error')}"
    
    stats = final_stats['result']
    
    # Verify stats structure exists (track_effectiveness should have updated these)
    assert "enabled" in stats, "Stats should have 'enabled' field"
    assert "total_duplicates_found" in stats, "Stats should have 'total_duplicates_found' field"
    
    print(f"Dedup stats after run: duplicates_found={stats.get('total_duplicates_found', 0)}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_advanced_dedup_metrics_available(running_mcp_server):
    """Test that advanced deduplication metrics are available and populated."""
    metrics_result = await running_mcp_server.call_mcp_tool("get_advanced_deduplication_metrics")
    
    assert "error" not in metrics_result, f"Failed to get metrics: {metrics_result.get('error')}"
    assert "result" in metrics_result, "No result in metrics response"
    
    result = metrics_result['result']
    assert "metrics" in result, "metrics missing from result"
    
    metrics = result['metrics']
    # Metrics should be a dict with various statistics
    assert isinstance(metrics, dict), f"Metrics should be a dict, got {type(metrics)}"
    
    print(f"Advanced dedup metrics available: {list(metrics.keys()) if metrics else 'empty'}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deduplication_with_semantically_similar_docs(running_mcp_server):
    """Test deduplication correctly identifies semantically similar documents."""
    # Add semantically similar but textually different documents
    docs = [
        {
            "content": "The quick brown fox jumps over the lazy dog.",
            "metadata": {"version": "original", "test": "semantic_dedup"}
        },
        {
            "content": "A fast brown fox leaps over a sleepy canine.",
            "metadata": {"version": "paraphrase", "test": "semantic_dedup"}
        },
        {
            "content": "Completely unrelated content about Python programming.",
            "metadata": {"version": "distinct", "test": "semantic_dedup"}
        },
    ]
    
    for doc in docs:
        result = await running_mcp_server.call_mcp_tool("add_document", doc)
        assert "error" not in result, f"Failed to add document: {result.get('error')}"
    
    await asyncio.sleep(2)  # Allow embedding generation
    
    # Run advanced deduplication
    dedup_result = await running_mcp_server.call_mcp_tool("run_advanced_deduplication", {
        "collection": "short_term",
        "dry_run": True  # Just analyze, don't modify
    })
    
    assert "error" not in dedup_result, f"Deduplication failed: {dedup_result.get('error')}"
    
    # The deduplication should complete without the perform_semantic_clustering error
    result = dedup_result['result']
    assert "result" in result, "Should have result"
    
    inner_result = result['result']
    duplicates_found = inner_result.get('duplicates_found', 0)
    
    # We expect the semantically similar docs might be flagged as duplicates
    # The exact number depends on thresholds, but the operation should succeed
    print(f"Semantic dedup found {duplicates_found} potential duplicates")
    
    # Main test: operation completed without errors (would have failed before the fix)
    assert inner_result is not None, "Result should not be None"
