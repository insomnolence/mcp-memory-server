from typing import List, Dict, Any


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get MCP tool definitions for the server.
    
    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "name": "add_document",
            "description": "Adds a document to the hierarchical memory system with intelligent importance scoring, automatic collection selection, and permanent storage support.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The full text content of the document to be added."
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata to associate with the document chunks. Include 'type' field for content categorization and 'permanence_flag': 'critical' for explicit permanent storage.",
                        "default": {}
                    },
                    "language": {
                        "type": "string",
                        "description": "The programming language or format of the content (e.g., 'python', 'c++', 'markdown', or 'text').",
                        "default": "text",
                        "enum": ["python", "c++", "markdown", "text"]
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Target memory collection ('auto' for automatic selection, 'short_term', or 'long_term').",
                        "default": "auto",
                        "enum": ["auto", "short_term", "long_term"]
                    },
                    "context": {
                        "type": "object",
                        "description": "Optional context information for importance scoring. Use 'permanence_requested': true to boost importance for permanent storage, 'is_solution': true for solutions, 'is_important': true for critical content.",
                        "default": {}
                    }
                },
                "required": ["content"]
            }
        },
        {
            "name": "query_documents",
            "description": "Queries the hierarchical memory system with intelligent multi-factor scoring across all collections, with optional reranking.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The natural language query to find relevant documents."
                    },
                    "collections": {
                        "type": "string",
                        "description": "Comma-separated list of collections to search ('short_term', 'long_term'). Default: all collections."
                    },
                    "k": {
                        "type": "integer",
                        "description": "Maximum number of results to return.",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    },
                    "use_reranker": {
                        "type": "boolean",
                        "description": "Whether to apply cross-encoder reranking for improved relevance.",
                        "default": True
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_memory_stats",
            "description": "Get comprehensive statistics about the memory system, including collection counts and status.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_lifecycle_stats",
            "description": "Get comprehensive lifecycle management statistics including TTL tiers, aging status, and maintenance health.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "start_background_maintenance",
            "description": "Start automatic background maintenance processes for TTL cleanup and aging refresh.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "stop_background_maintenance",
            "description": "Stop automatic background maintenance processes.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "query_permanent_documents",
            "description": "Query only permanent documents that never expire (importance ≥ 0.95 or explicitly marked permanent).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The natural language query to find relevant permanent documents."
                    },
                    "k": {
                        "type": "integer",
                        "description": "Maximum number of results to return.",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_permanence_stats",
            "description": "Get statistics about permanent content in the memory system.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "deduplicate_memories",
            "description": "Manually trigger deduplication process on specified collections to remove duplicate content and optimize storage.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collections": {
                        "type": "string",
                        "description": "Comma-separated list of collections to deduplicate ('short_term', 'long_term'). Default: all collections.",
                        "default": "short_term,long_term"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, only analyze and report potential duplicates without making changes.",
                        "default": false
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_deduplication_stats",
            "description": "Get comprehensive statistics about deduplication effectiveness, storage savings, and system performance.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "preview_duplicates",
            "description": "Preview potential duplicate documents without removing them, showing similarity scores and merge candidates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection to analyze for duplicates ('short_term' or 'long_term').",
                        "enum": ["short_term", "long_term"],
                        "default": "short_term"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of duplicate pairs to show.",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": []
            }
        }
    ]