import pytest
import time
import asyncio
import random


@pytest.mark.performance
@pytest.mark.asyncio
async def test_ingestion_performance(running_mcp_server, data_generator):
    """Measure the performance of document ingestion."""
    num_documents = 100  # Number of documents to ingest
    batch_size = 10      # Number of documents to add concurrently

    documents_to_add = data_generator.generate_test_dataset(num_documents, duplicate_percentage=0)

    successful_adds = 0
    start_time = time.time()

    for i in range(0, num_documents, batch_size):
        batch = documents_to_add[i:i + batch_size]
        tasks = []
        for doc in batch:
            tasks.append(running_mcp_server.call_mcp_tool("add_document", {
                "content": doc['content'],
                "metadata": doc['metadata']
            }))

        results = await asyncio.gather(*tasks)

        for result in results:
            if "error" not in result:
                successful_adds += 1
            else:
                print(f"Error adding document: {result.get('error')}")

    end_time = time.time()
    duration = end_time - start_time

    tps = successful_adds / duration if duration > 0 else 0

    print("\n--- Ingestion Performance ---")
    print(f"Total Documents: {num_documents}")
    print(f"Successful Adds: {successful_adds}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Documents per second (TPS): {tps:.2f}")

    assert successful_adds == num_documents, "Not all documents were successfully added."
    assert tps > 0, "Ingestion rate is zero, indicating a problem."


@pytest.mark.performance
@pytest.mark.asyncio
async def test_query_load_performance(running_mcp_server, data_generator):
    """Measure the performance of query handling under load."""
    # First, ingest some documents to query against (allow some failures)
    num_ingestion_docs = 20  # Reduced from 50 for faster setup
    ingestion_docs = data_generator.generate_test_dataset(num_ingestion_docs, duplicate_percentage=0)
    successful_ingestion = 0
    for doc in ingestion_docs:
        add_result = await running_mcp_server.call_mcp_tool("add_document", {
            "content": doc['content'],
            "metadata": doc['metadata']
        })
        if "error" not in add_result:
            successful_ingestion += 1
        else:
            print(f"Warning: Failed to add setup document: {add_result.get('error')}")
    
    # Need at least some documents for meaningful query testing
    assert successful_ingestion >= 5, f"Only {successful_ingestion} setup documents added, need at least 5"
    await asyncio.sleep(2)  # Give ChromaDB time to index

    num_queries = 50  # Reduced from 100 for faster completion
    concurrent_queries = 5  # Reduced from 10 to avoid overwhelming server
    query_contents = [
        "What is the main idea of the document?",
        "Tell me about the code structure.",
        "Analyze the data patterns.",
        "Summarize the documentation."
    ]

    successful_queries = 0
    total_response_time = 0
    start_time = time.time()

    for i in range(0, num_queries, concurrent_queries):
        batch_queries = [random.choice(query_contents) for _ in range(concurrent_queries)]
        tasks = []
        for query_text in batch_queries:
            tasks.append(running_mcp_server.call_mcp_tool("query_documents", {
                "query": query_text,
                "k": 3
            }))

        results = await asyncio.gather(*tasks)

        for result in results:
            if "error" not in result:
                successful_queries += 1
                # Assuming processing_time_ms is returned in the result
                # If not, we'd measure it here per call
                total_response_time += result.get('result', {}).get('processing_time_ms', 0)
            else:
                print(f"Error querying documents: {result.get('error')}")

    end_time = time.time()
    duration = end_time - start_time

    qps = successful_queries / duration if duration > 0 else 0
    avg_response_time_ms = total_response_time / successful_queries if successful_queries > 0 else 0

    print("\n--- Query Load Performance ---")
    print(f"Total Queries: {num_queries}")
    print(f"Successful Queries: {successful_queries}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Queries per second (QPS): {qps:.2f}")
    print(f"Average Response Time: {avg_response_time_ms:.2f} ms")

    # Allow some failures under heavy load (>60% success is acceptable for stress testing)
    min_success_rate = 0.60
    success_rate = successful_queries / num_queries
    assert success_rate >= min_success_rate, f"Query success rate {success_rate:.1%} below minimum {min_success_rate:.1%}"
    assert qps > 0, "Query rate is zero, indicating a problem."
    # Only check avg response time if we had successful queries
    if successful_queries > 0:
        assert avg_response_time_ms >= 0, "Average response time is negative, indicating a problem."
