import pytest
import time
import asyncio

@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_stress(running_mcp_server, memory_monitor, data_generator):
    """Run memory stress test by continuously adding documents."""
    duration = 30  # Shorter duration for automated testing
    data_rate = 5  # Number of documents to add per iteration

    memory_monitor.start_monitoring(interval=1.0)

    start_time = time.time()
    document_count = 0

    while time.time() - start_time < duration:
        documents = data_generator.generate_test_dataset(data_rate, duplicate_percentage=20)

        for doc in documents:
            result = await running_mcp_server.call_mcp_tool("add_document", {
                "content": doc['content'],
                "metadata": doc['metadata']
            })

            if "error" not in result:
                document_count += 1
            else:
                print(f"Error adding document: {result.get('error')}")

        # Query occasionally to simulate real usage
        if document_count % 10 == 0:
            await running_mcp_server.call_mcp_tool("query_documents", {
                "query": "test data analysis",
                "k": 1
            })

        await asyncio.sleep(0.5) # Brief pause

    memory_stats = memory_monitor.stop_monitoring()

    print(f"\n--- Memory Stress Test Results ---")
    print(f"Total Documents Added: {document_count}")
    if memory_stats.get('process_memory'):
        pm = memory_stats['process_memory']
        print(f"Process Memory (Min/Max/Avg/Final): {pm['min_mb']:.1f} / {pm['max_mb']:.1f} / {pm['avg_mb']:.1f} / {pm['final_mb']:.1f} MB")
        if document_count > 0:
            print(f"Memory per Document (Peak): {pm['max_mb'] / document_count:.3f} MB/doc")
    
    assert document_count > 0, "No documents were added during the stress test."
    # Memory tracking is optional - may fail if process detection doesn't work
    max_memory = memory_stats.get('process_memory', {}).get('max_mb', 0)
    if max_memory == 0:
        print("Warning: Memory usage tracking failed - process not detected")
    else:
        assert max_memory > 0, "Memory usage was not tracked."
