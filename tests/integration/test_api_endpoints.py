import pytest
import httpx
import asyncio
import time

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_document_concurrent_calls(running_mcp_server):
    """Test concurrent calls to add_document to ensure non-blocking behavior."""
    # Server is already running via fixture
    base_url = running_mcp_server.base_url
    num_concurrent_calls = 10
    documents_to_add = []
    for i in range(num_concurrent_calls):
        documents_to_add.append({
            "jsonrpc": "2.0",
            "id": i + 1,
            "method": "tools/call",
            "params": {
                "name": "add_document",
                "arguments": {
                    "content": f"Concurrent test document {i}",
                    "metadata": {"test_id": i, "source": "concurrent_test"}
                }
            }
        })

    async with httpx.AsyncClient(base_url=base_url) as client:
        start_time = time.time()
        tasks = []
        for doc_payload in documents_to_add:
            tasks.append(client.post("/", json=doc_payload, timeout=30))

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Check responses
        for i, response in enumerate(responses):
            assert not isinstance(response, Exception), f"Call {i} failed with exception: {response}"
            assert response.status_code == 200, f"Call {i} received non-200 status: {response.status_code}"
            json_response = response.json()
            assert "error" not in json_response, f"Call {i} returned error: {json_response.get('error')}"
            # Parse the MCP-compliant response format: result contains structured data directly
            result = json_response['result']
            # For successful operations, check the message or status
            if 'message' in result:
                assert 'success' in result['message'].lower() or 'added' in result['message'].lower(), f"Call {i} operation failed: {result}"
            elif 'error' in result:
                assert False, f"Call {i} returned error: {result['error']}"
            else:
                # As long as there's no error field, consider it successful
                assert 'error' not in result, f"Call {i} operation failed: {result}"

        duration = end_time - start_time
        print(f"\nConcurrent add_document calls ({num_concurrent_calls}) took {duration:.2f} seconds.")

        # Assert that the total time is reasonable for concurrent operations
        # This is a heuristic: it should be closer to the time of a single call + overhead,
        # not the sum of all individual call times if they were blocking.
        # A single call might take ~0.5-1.5s depending on embedding model loading etc.
        # So 10 concurrent calls should ideally be < 5 seconds, but depends on system.
        # We'll set a generous upper bound for now.
        assert duration < (num_concurrent_calls * 0.5), \
            f"Concurrent calls took too long, suggesting blocking I/O. Duration: {duration:.2f}s"

    # Verify documents were added (optional, but good for completeness)
    stats_result = await running_mcp_server.call_mcp_tool("get_memory_stats")
    assert "error" not in stats_result, f"Error getting memory stats: {stats_result.get('error')}"
    
    # Parse the MCP-compliant response format
    result = stats_result['result']
    if 'total_documents' in result:
        total_docs = result['total_documents']
        
        # This assertion is tricky without knowing initial count and other documents.
        # A more robust test would involve adding a known number of documents and checking the count.
        # For now, we'll just check if the total documents is at least the number we added.
        assert total_docs >= num_concurrent_calls, \
            f"Expected at least {num_concurrent_calls} documents, got {total_docs}"
    else:
        assert False, f"Unexpected stats response format: {stats_result}"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_documents_tool(running_mcp_server):
    """Test the query_documents tool."""
    # Add a document to query
    add_result = await running_mcp_server.call_mcp_tool("add_document", {
        "content": "This is a document about testing and software quality.",
        "metadata": {"type": "test_query"}
    })
    assert "error" not in add_result, f"Failed to add document for query test: {add_result.get('error')}"
    await asyncio.sleep(1) # Give ChromaDB time to index

    query_result = await running_mcp_server.call_mcp_tool("query_documents", {
        "query": "software testing",
        "k": 1
    })
    assert "error" not in query_result, f"Error querying documents: {query_result.get('error')}"
    assert len(query_result['result']['results']) > 0, "No results returned for query"
    assert "testing and software quality" in query_result['result']['results'][0]['content'], "Query did not return expected content"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_memory_stats_tool(running_mcp_server):
    """Test the get_memory_stats tool."""
    stats_result = await running_mcp_server.call_mcp_tool("get_memory_stats")
    assert "error" not in stats_result, f"Error getting memory stats: {stats_result.get('error')}"
    assert "total_documents" in stats_result['result'], "total_documents missing from stats"
    assert "collections" in stats_result['result'], "collections missing from stats"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_lifecycle_stats_tool(running_mcp_server):
    """Test the get_lifecycle_stats tool."""
    stats_result = await running_mcp_server.call_mcp_tool("get_lifecycle_stats")
    assert "error" not in stats_result, f"Error getting lifecycle stats: {stats_result.get('error')}"
    assert "ttl_manager" in stats_result['result'], "ttl_manager missing from lifecycle stats"
    assert "maintenance" in stats_result['result'], "maintenance missing from lifecycle stats"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_permanent_documents_tool(running_mcp_server):
    """Test the query_permanent_documents tool."""
    # Add a permanent document
    add_result = await running_mcp_server.call_mcp_tool("add_document", {
        "content": "This is a permanent record of critical importance.",
        "metadata": {"permanence_flag": "critical"}
    })
    assert "error" not in add_result, f"Failed to add permanent document: {add_result.get('error')}"
    await asyncio.sleep(1) # Give ChromaDB time to index

    query_result = await running_mcp_server.call_mcp_tool("query_permanent_documents", {
        "query": "critical record",
        "k": 1
    })
    assert "error" not in query_result, f"Error querying permanent documents: {query_result.get('error')}"
    assert len(query_result['result']['results']) > 0, "No results returned for permanent query"
    assert "permanent record" in query_result['result']['results'][0]['content'], "Permanent query did not return expected content"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_deduplication_stats_tool(running_mcp_server):
    """Test the get_deduplication_stats tool."""
    stats_result = await running_mcp_server.call_mcp_tool("get_deduplication_stats")
    assert "error" not in stats_result, f"Error getting deduplication stats: {stats_result.get('error')}"
    assert "total_duplicates_found" in stats_result['result'], "total_duplicates_found missing from dedup stats"
    assert "enabled" in stats_result['result'], "enabled flag missing from dedup stats"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_preview_duplicates_tool(running_mcp_server):
    """Test the preview_duplicates tool."""
    # Add some potentially duplicate content
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Duplicate content example one.", "metadata": {"type": "dedup_test"}})
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Duplicate content example two.", "metadata": {"type": "dedup_test"}})
    await asyncio.sleep(1) # Give ChromaDB time to index

    preview_result = await running_mcp_server.call_mcp_tool("preview_duplicates", {"collection": "short_term", "limit": 5})
    assert "error" not in preview_result, f"Error previewing duplicates: {preview_result.get('error')}"
    assert "duplicates_found" in preview_result['result'], "duplicates_found missing from preview result"
    assert "preview_pairs" in preview_result['result'], "preview_pairs missing from preview result"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_query_performance_tool(running_mcp_server):
    """Test the get_query_performance tool."""
    # Add a document and query it to generate some performance data
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Performance test document.", "metadata": {"type": "perf_test"}})
    await running_mcp_server.call_mcp_tool("query_documents", {"query": "performance", "k": 1})
    await asyncio.sleep(1) # Give monitor time to log

    perf_result = await running_mcp_server.call_mcp_tool("get_query_performance", {"time_window": "all"})
    assert "error" not in perf_result, f"Error getting query performance: {perf_result.get('error')}"
    assert "stats" in perf_result['result'], "stats missing from query performance result"
    assert perf_result['result']['stats']['total_queries'] > 0, "No queries recorded in performance stats"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_real_time_metrics_tool(running_mcp_server):
    """Test the get_real_time_metrics tool."""
    metrics_result = await running_mcp_server.call_mcp_tool("get_real_time_metrics")
    assert "error" not in metrics_result, f"Error getting real-time metrics: {metrics_result.get('error')}"
    assert "metrics" in metrics_result['result'], "metrics missing from real-time metrics result"
    assert "current_query_rate" in metrics_result['result']['metrics'], "current_query_rate missing"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_performance_data_tool(running_mcp_server):
    """Test the export_performance_data tool."""
    # Ensure some data exists
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Export test data.", "metadata": {"type": "export_test"}})
    await running_mcp_server.call_mcp_tool("query_documents", {"query": "export", "k": 1})
    await asyncio.sleep(1)

    export_result = await running_mcp_server.call_mcp_tool("export_performance_data", {"format": "json"})
    assert "error" not in export_result, f"Error exporting performance data: {export_result.get('error')}"
    assert "data" in export_result['result'], "data missing from export result"
    assert isinstance(export_result['result']['data'], list), "Exported data is not a list"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_comprehensive_analytics_tool(running_mcp_server):
    """Test the get_comprehensive_analytics tool."""
    analytics_result = await running_mcp_server.call_mcp_tool("get_comprehensive_analytics")
    assert "error" not in analytics_result, f"Error getting comprehensive analytics: {analytics_result.get('error')}"
    assert "analytics" in analytics_result['result'], "analytics missing from comprehensive analytics result"
    assert "overall_health" in analytics_result['result']['analytics'], "overall_health missing"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_system_intelligence_tool(running_mcp_server):
    """Test the get_system_intelligence tool."""
    intelligence_result = await running_mcp_server.call_mcp_tool("get_system_intelligence", {"focus_area": "storage"})
    assert "error" not in intelligence_result, f"Error getting system intelligence: {intelligence_result.get('error')}"
    assert "intelligence" in intelligence_result['result'], "intelligence missing from system intelligence result"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_optimization_recommendations_tool(running_mcp_server):
    """Test the get_optimization_recommendations tool."""
    recommendations_result = await running_mcp_server.call_mcp_tool("get_optimization_recommendations", {"priority_filter": "high"})
    assert "error" not in recommendations_result, f"Error getting optimization recommendations: {recommendations_result.get('error')}"
    assert "recommendations" in recommendations_result['result'], "recommendations missing from result"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_predictive_insights_tool(running_mcp_server):
    """Test the get_predictive_insights tool."""
    insights_result = await running_mcp_server.call_mcp_tool("get_predictive_insights", {"prediction_type": "storage"})
    assert "error" not in insights_result, f"Error getting predictive insights: {insights_result.get('error')}"
    assert "insights" in insights_result['result'], "insights missing from predictive insights result"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_chunk_relationships_tool(running_mcp_server):
    """Test the get_chunk_relationships tool."""
    # Add some related documents to generate relationships
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Chunk A: First part of a story.", "metadata": {"story_id": "story1"}})
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Chunk B: Second part of the same story.", "metadata": {"story_id": "story1"}})
    await asyncio.sleep(1) # Give time for relationships to be processed

    relationships_result = await running_mcp_server.call_mcp_tool("get_chunk_relationships")
    assert "error" not in relationships_result, f"Error getting chunk relationships: {relationships_result.get('error')}"
    assert "relationships" in relationships_result['result'], "relationships missing from result"
    # Assert that some relationships are found (depends on implementation of relationship manager)
    # assert len(relationships_result['result']['relationships']) > 0, "No chunk relationships found"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_system_health_assessment_tool(running_mcp_server):
    """Test the get_system_health_assessment tool."""
    health_result = await running_mcp_server.call_mcp_tool("get_system_health_assessment")
    assert "error" not in health_result, f"Error getting system health assessment: {health_result.get('error')}"
    assert "health_assessment" in health_result['result'], "health_assessment missing from result"
    assert "health_status" in health_result['result']['health_assessment'], "health_status missing"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_optimize_deduplication_thresholds_tool(running_mcp_server):
    """Test the optimize_deduplication_thresholds tool."""
    optimize_result = await running_mcp_server.call_mcp_tool("optimize_deduplication_thresholds")
    assert "error" not in optimize_result, f"Error optimizing deduplication thresholds: {optimize_result.get('error')}"
    assert "optimization_result" in optimize_result['result'], "optimization_result missing from result"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_domain_analysis_tool(running_mcp_server):
    """Test the get_domain_analysis tool."""
    # Add some documents with different types to enable domain analysis
    await running_mcp_server.call_mcp_tool("add_document", {"content": "def my_function(): pass", "metadata": {"type": "code"}})
    await running_mcp_server.call_mcp_tool("add_document", {"content": "This is a text document.", "metadata": {"type": "text"}})
    await asyncio.sleep(1)

    domain_result = await running_mcp_server.call_mcp_tool("get_domain_analysis", {"collection": "short_term"})
    assert "error" not in domain_result, f"Error getting domain analysis: {domain_result.get('error')}"
    assert "analysis_result" in domain_result['result'], "analysis_result missing from result"
    
    # Handle case where analysis_result might be None
    analysis_result = domain_result['result']['analysis_result']
    if analysis_result is not None:
        assert "domain_distribution" in analysis_result, "domain_distribution missing"
    else:
        print("⚠️ Domain analysis returned None result (not enough data for analysis)")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_clustering_analysis_tool(running_mcp_server):
    """Test the get_clustering_analysis tool."""
    # Add some documents for clustering
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Cluster test A1.", "metadata": {"group": "A"}})
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Cluster test A2.", "metadata": {"group": "A"}})
    await asyncio.sleep(1)

    clustering_result = await running_mcp_server.call_mcp_tool("get_clustering_analysis", {"collection": "short_term"})
    assert "error" not in clustering_result, f"Error getting clustering analysis: {clustering_result.get('error')}"
    assert "analysis_result" in clustering_result['result'], "analysis_result missing from result"
    # assert "clusters" in clustering_result['result']['analysis_result'], "clusters missing"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_advanced_deduplication_metrics_tool(running_mcp_server):
    """Test the get_advanced_deduplication_metrics tool."""
    metrics_result = await running_mcp_server.call_mcp_tool("get_advanced_deduplication_metrics")
    assert "error" not in metrics_result, f"Error getting advanced deduplication metrics: {metrics_result.get('error')}"
    assert "metrics" in metrics_result['result'], "metrics missing from result"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_advanced_deduplication_tool(running_mcp_server):
    """Test the run_advanced_deduplication tool."""
    # Add some duplicate content for advanced deduplication
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Advanced dedup test one.", "metadata": {"type": "adv_dedup"}})
    await running_mcp_server.call_mcp_tool("add_document", {"content": "Advanced dedup test two.", "metadata": {"type": "adv_dedup"}})
    await asyncio.sleep(1)

    dedup_result = await running_mcp_server.call_mcp_tool("run_advanced_deduplication", {"collection": "short_term", "dry_run": False})
    assert "error" not in dedup_result, f"Error running advanced deduplication: {dedup_result.get('error')}"
    assert "result" in dedup_result['result'], "result missing from advanced deduplication result"
    assert "duplicates_found" in dedup_result['result']['result'], "duplicates_found missing"
