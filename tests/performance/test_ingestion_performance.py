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

    print(f"\n--- Ingestion Performance ---")
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
    # First, ingest some documents to query against
    num_ingestion_docs = 50
    ingestion_docs = data_generator.generate_test_dataset(num_ingestion_docs, duplicate_percentage=0)
    for doc in ingestion_docs:
        add_result = await running_mcp_server.call_mcp_tool("add_document", {
            "content": doc['content'],
            "metadata": doc['metadata']
        })
        assert "error" not in add_result, f"Failed to add document for query test: {add_result.get('error')}"
    await asyncio.sleep(2) # Give ChromaDB time to index

    num_queries = 100
    concurrent_queries = 10
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

    print(f"\n--- Query Load Performance ---")
    print(f"Total Queries: {num_queries}")
    print(f"Successful Queries: {successful_queries}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Queries per second (QPS): {qps:.2f}")
    print(f"Average Response Time: {avg_response_time_ms:.2f} ms")

    assert successful_queries == num_queries, "Not all queries were successful."
    assert qps > 0, "Query rate is zero, indicating a problem."
    assert avg_response_time_ms > 0, "Average response time is zero, indicating a problem."
