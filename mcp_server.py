import os
from fastapi import FastAPI, Request
from pydantic import BaseModel
from chromadb import PersistentClient
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_chroma import Chroma
from langchain_core.documents import Document
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio
from typing import List, Dict, Any, Optional

# --- ChromaDB Setup ---
collection_name = "project_memory_advanced"
persist_directory = "./chroma_db_advanced"

# Embedding Model
embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
embedding_function = HuggingFaceEmbeddings(model_name=embedding_model_name)

# Initialize the Chroma vector store through the LangChain wrapper
vectorstore = Chroma(
    collection_name=collection_name,
    embedding_function=embedding_function,
    persist_directory=persist_directory,
)

# --- Reranker Setup ---
reranker_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# Initialize FastAPI app
app = FastAPI(title="Advanced Project Memory MCP Server")

# --- Protocol Data Models ---
class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int]
    result: Any

class JsonRpcError(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    error: Dict[str, Any]

# --- Tool Functions ---
def add_document_tool(content: str, metadata: dict = None, language: str = "text") -> dict:
    """Add a document to the vector store."""
    try:
        language_map = {
            "python": Language.PYTHON,
            "c++": Language.CPP,
            "markdown": Language.MARKDOWN,
        }
        lang_enum = language_map.get(language.lower(), None)
        
        if lang_enum:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=lang_enum, chunk_size=1000, chunk_overlap=100
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=100
            )
        
        chunks = splitter.split_text(content)
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = metadata.copy() if metadata else {}
            doc_metadata.update({
                "language": language,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })
            documents.append(Document(page_content=chunk, metadata=doc_metadata))
        
        vectorstore.add_documents(documents)
        
        return {
            "success": True,
            "message": f"Added {len(documents)} document chunks to the vector store.",
            "chunks_added": len(documents)
        }
    except Exception as e:
        raise Exception(f"Failed to add document: {str(e)}")

def query_documents_tool(query: str) -> dict:
    """Query documents from the vector store with reranking."""
    try:
        initial_docs = vectorstore.similarity_search(query, k=20)
        
        if not initial_docs:
            return {
                "success": True,
                "results": [],
                "message": "No documents found matching the query."
            }
        
        doc_texts = [doc.page_content for doc in initial_docs]
        query_doc_pairs = [(query, doc_text) for doc_text in doc_texts]
        
        reranker_scores = reranker_model.predict(query_doc_pairs)
        
        scored_docs = list(zip(initial_docs, reranker_scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc, score in scored_docs[:5]:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": float(score)
            })
        
        # Format results as MCP content blocks for Claude Code compatibility
        content_blocks = []
        for doc in results:
            content_blocks.append({
                "type": "text",
                "text": f"**Relevance: {doc['relevance_score']:.2f}**\n\n{doc['content']}\n\n**Metadata:** {doc['metadata']}"
            })
        
        return {
            "content": content_blocks
        }
    except Exception as e:
        raise Exception(f"Failed to query documents: {str(e)}")

# --- Tool and Resource Registries (CRITICAL FOR COMPLIANCE) ---
tool_registry = {
    "add_document": add_document_tool,
    "query_documents": query_documents_tool,
}

tool_definitions = [
    {
        "name": "add_document",
        "description": "Adds a document to the vector store for later retrieval. The language of the content can be specified to improve chunking and splitting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The full text content of the document to be added."
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata to associate with the document chunks, such as source or title.",
                    "default": {}
                },
                "language": {
                    "type": "string",
                    "description": "The programming language or format of the content (e.g., 'python', 'c++', 'markdown', or 'text').",
                    "default": "text",
                    "enum": ["python", "c++", "markdown", "text"]
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "query_documents",
        "description": "Queries the vector store for documents semantically similar to a given query, and then reranks them for precision.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The natural language query to find relevant documents."
                }
            },
            "required": ["query"]
        }
    }
]

# --- Conceptual Resource Handlers ---
async def list_resources_handler() -> List[dict]:
    """Conceptually lists documents in the vector store as resources."""
    return [
        {"id": "doc_123", "name": "Project README", "type": "text/markdown"},
        {"id": "doc_456", "name": "main.py", "type": "text/x-python"},
    ]

async def read_resource_handler(resource_id: str) -> dict:
    """Conceptually reads a specific document from the vector store."""
    if resource_id == "doc_123":
        return {"content": "# Project Title\nThis is the project README file..."}
    elif resource_id == "doc_456":
        return {"content": "import os\n\nprint('hello world')"}
    else:
        raise ValueError(f"Resource '{resource_id}' not found.")

# --- Corrected event_generator function ---
async def event_generator():
    """
    Handles the SSE connection for the Gemini CLI.
    Sends the 'mcp-ready' event and then keeps the connection alive with heartbeats.
    """
    yield "event: mcp-ready\ndata: {}\n\n"

    try:
        while True:
            await asyncio.sleep(10)
            yield "data: heartbeat\n\n"
    except asyncio.CancelledError:
        pass


# --- Combined JSON-RPC and SSE Endpoint ---
@app.api_route("/", methods=["GET", "POST"], response_class=JSONResponse)
async def json_rpc_handler(request: Request):
    if request.method == "GET":
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    if request.method == "POST":
        try:
            body = await request.json()
            rpc_request = JsonRpcRequest(**body)
            method = rpc_request.method
            rpc_id = rpc_request.id

            if rpc_id is None:
                if method == "notifications/initialized":
                    print("Received 'notifications/initialized' from client.")
                return

            if method == "initialize":
                response = JsonRpcResponse(
                    id=rpc_id,
                    result={
                        "protocolVersion": "2025-06-18",
                        "capabilities": {
                            "tools": {},
                            "resources": {}
                        },
                        "serverInfo": {
                            "name": "Project Memory MCP Server",
                            "version": "1.0.0",
                            "serverURL": "http://128.0.0.1:8080/"
                        },
                        "tools": tool_definitions
                    }
                )
                return JSONResponse(content=response.dict(), media_type="application/json-rpc")

            elif method == "tools/list":
                response = JsonRpcResponse(
                    id=rpc_id, 
                    result={
                        "tools": tool_definitions
                    }
                )
                return JSONResponse(content=response.dict(), media_type="application/json-rpc")
            
            elif method == "resources/list":
                resources = await list_resources_handler()
                response = JsonRpcResponse(id=rpc_id, result={"resources": resources})
                return JSONResponse(content=response.dict(), media_type="application/json-rpc")
            
            elif method == "resources/read":
                params = rpc_request.params or {}
                resource_id = params.get("resourceId")
                if not resource_id:
                    raise ValueError("`resourceId` parameter is required for `resources/read`.")
                
                content = await read_resource_handler(resource_id)
                response = JsonRpcResponse(id=rpc_id, result=content)
                return JSONResponse(content=response.dict(), media_type="application/json-rpc")

            elif method == "tools/call":
                params = rpc_request.params or {}
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                tool_func = tool_registry.get(tool_name)
                if not tool_func:
                    error_response = JsonRpcError(
                        id=rpc_id,
                        error={
                            "code": -32601,
                            "message": f"Tool '{tool_name}' not found."
                        }
                    )
                    return JSONResponse(content=error_response.dict(), status_code=400)
                
                result = tool_func(**tool_args)
                response = JsonRpcResponse(id=rpc_id, result=result)
                return JSONResponse(content=response.dict(), media_type="application/json-rpc")

            else:
                error_response = JsonRpcError(
                    id=rpc_id,
                    error={
                        "code": -32601,
                        "message": f"Method '{method}' not found."
                    }
                )
                return JSONResponse(content=error_response.dict(), status_code=400)

        except Exception as e:
            error_id = rpc_id if 'rpc_id' in locals() and rpc_id is not None else None
            error_response = JsonRpcError(
                id=error_id,
                error={
                    "code": -32000,
                    "message": f"An unexpected error occurred: {str(e)}"
                }
            )
            return JSONResponse(content=error_response.dict(), status_code=500)
