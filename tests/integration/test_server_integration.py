import pytest
import time


@pytest.mark.integration
@pytest.mark.asyncio
async def test_server_health(running_mcp_server):
    """Test server health endpoint"""
    response = running_mcp_server.is_server_running()
    assert response is True, "Server health check failed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_stats(running_mcp_server):
    """Test memory statistics endpoint"""
    result = await running_mcp_server.call_mcp_tool("get_memory_stats")
    assert "error" not in result, f"Error calling get_memory_stats: {result.get('error')}"
    assert "collections" in str(result), "Memory stats response missing 'collections'"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_ingestion(running_mcp_server, data_generator):
    """Test data ingestion performance"""
    count = 10  # Reduced count for quick integration test
    documents = data_generator.generate_test_dataset(count, duplicate_percentage=10)

    successful_adds = 0
    for doc in documents:
        result = await running_mcp_server.call_mcp_tool("add_document", {
            "content": doc['content'],
            "metadata": doc['metadata']
        })
        if "error" not in result:
            successful_adds += 1

    assert successful_adds == count, f"Expected {count} successful adds, but got {successful_adds}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_performance(running_mcp_server):
    """Test query performance"""
    # First, add a document to query against
    await running_mcp_server.call_mcp_tool("add_document", {
        "content": "This is a test document about data analysis and machine learning.",
        "metadata": {"type": "test", "source": "query_test"}
    })
    time.sleep(1)  # Give ChromaDB time to process

    test_queries = [
        "data analysis",
        "machine learning"
    ]

    for query in test_queries:
        result = await running_mcp_server.call_mcp_tool("query_documents", {
            "query": query,
            "k": 1
        })
        assert "error" not in result, f"Error calling query_documents for '{query}': {result.get('error')}"
        assert len(result['result'].get('results', [])), f"No results for query: {query}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deduplication_features(running_mcp_server):
    """Test deduplication features"""
    # Test deduplication stats
    result = await running_mcp_server.call_mcp_tool("get_deduplication_stats")
    assert "error" not in result, f"Error calling get_deduplication_stats: {result.get('error')}"
    assert "total_duplicates_found" in str(result), "Deduplication stats missing 'total_duplicates_found'"

    # Test preview duplicates
    result = await running_mcp_server.call_mcp_tool("preview_duplicates", {"limit": 1})
    assert "error" not in result, f"Error calling preview_duplicates: {result.get('error')}"
    assert "preview_pairs" in str(result), "Preview duplicates response missing 'preview_pairs'"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analytics_features(running_mcp_server):
    """Test analytics and intelligence features"""
    analytics_tools = [
        'get_comprehensive_analytics',
        'get_system_intelligence',
        'get_optimization_recommendations',
        'get_predictive_insights',
        'get_chunk_relationships',
        'get_system_health_assessment'
    ]

    for tool in analytics_tools:
        result = await running_mcp_server.call_mcp_tool(tool)
        assert "error" not in result, f"Error calling {tool}: {result.get('error')}"
        # Check that we have a valid MCP response structure
        assert "result" in result, f"Response for {tool} missing 'result' field"
        assert isinstance(result["result"], dict), f"Response result for {tool} is not a dict"
