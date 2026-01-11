from typing import List, Dict, Any


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get MCP tool definitions for the server.

    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "name": "add_document",
            "description": (
                "Adds a document to the hierarchical memory system with intelligent "
                "importance scoring, automatic collection selection, and permanent "
                "storage support."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The full text content of the document to be added."
                    },
                    "metadata": {
                        "type": "object",
                        "description": (
                            "Optional metadata to associate with the document chunks. "
                            "Include 'type' field for content categorization and "
                            "'permanence_flag': 'critical' for explicit permanent storage."
                        ),
                        "default": {}
                    },
                    "language": {
                        "type": "string",
                        "description": (
                            "The programming language or format of the content "
                            "(e.g., 'python', 'c++', 'markdown', or 'text')."
                        ),
                        "default": "text",
                        "enum": ["python", "c++", "markdown", "text"]
                    },
                    "memory_type": {
                        "type": "string",
                        "description": (
                            "Target memory collection ('auto' for automatic selection, "
                            "'short_term', or 'long_term')."
                        ),
                        "default": "auto",
                        "enum": ["auto", "short_term", "long_term"]
                    },
                    "context": {
                        "type": "object",
                        "description": (
                            "Optional context information for importance scoring. "
                            "Use 'permanence_requested': true to boost importance for "
                            "permanent storage, 'is_solution': true for solutions, "
                            "'is_important': true for critical content."
                        ),
                        "default": {}
                    }
                },
                "required": ["content"]
            }
        },
        {
            "name": "query_documents",
            "description": (
                "Queries the hierarchical memory system with intelligent multi-factor "
                "scoring across all collections, with optional reranking."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The natural language query to find relevant documents."
                    },
                    "collections": {
                        "type": "string",
                        "description": (
                            "Comma-separated list of collections to search "
                            "('short_term', 'long_term'). Default: all collections."
                        )
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
                        "description": (
                            "Whether to apply cross-encoder reranking for improved relevance."
                        ),
                        "default": True
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_memory_stats",
            "description": (
                "Get comprehensive statistics about the memory system, "
                "including collection counts and status."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_lifecycle_stats",
            "description": (
                "Get comprehensive lifecycle management statistics including "
                "TTL tiers, aging status, and maintenance health."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "start_background_maintenance",
            "description": (
                "Start automatic background maintenance processes for "
                "TTL cleanup and aging refresh."
            ),
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
            "name": "cleanup_expired_memories",
            "description": (
                "Manually trigger cleanup of expired documents based on TTL. "
                "Useful for testing and immediate cleanup."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": (
                            "Specific collection to clean ('short_term' or 'long_term'). "
                            "If not specified, cleans all collections."
                        ),
                        "enum": ["short_term", "long_term"]
                    }
                },
                "required": []
            }
        },
        {
            "name": "query_permanent_documents",
            "description": (
                "Query only permanent documents that never expire "
                "(importance >= 0.95 or explicitly marked permanent)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The natural language query to find relevant permanent documents."
                        )
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
            "description": (
                "Manually trigger deduplication process on specified collections "
                "to remove duplicate content and optimize storage."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collections": {
                        "type": "string",
                        "description": (
                            "Comma-separated list of collections to deduplicate "
                            "('short_term', 'long_term'). Default: all collections."
                        ),
                        "default": "short_term,long_term"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": (
                            "If true, only analyze and report potential duplicates "
                            "without making changes."
                        ),
                        "default": False
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_deduplication_stats",
            "description": (
                "Get comprehensive statistics about deduplication effectiveness, "
                "storage savings, and system performance."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "preview_duplicates",
            "description": (
                "Preview potential duplicate documents without removing them, "
                "showing similarity scores and merge candidates."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": (
                            "Collection to analyze for duplicates "
                            "('short_term' or 'long_term')."
                        ),
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
        },
        {
            "name": "get_query_performance",
            "description": (
                "Get comprehensive query performance statistics including response "
                "times, quality metrics, and deduplication impact for analysis "
                "and optimization."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "time_window": {
                        "type": "string",
                        "description": "Time window for performance statistics.",
                        "enum": ["hour", "day", "week", "all"],
                        "default": "day"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_real_time_metrics",
            "description": (
                "Get real-time performance metrics and system status indicators "
                "including current query rates, response health, and system load."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "export_performance_data",
            "description": (
                "Export performance monitoring data in various formats for "
                "external analysis, reporting, or archival purposes."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Export format for performance data.",
                        "enum": ["json", "dict", "csv"],
                        "default": "json"
                    },
                    "time_window": {
                        "type": "string",
                        "description": "Time window for data export.",
                        "enum": ["hour", "day", "week", "all"],
                        "default": "all"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_comprehensive_analytics",
            "description": (
                "Get system analytics including storage patterns, deduplication "
                "effectiveness, query performance metrics, and optimization "
                "recommendations."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_system_intelligence",
            "description": (
                "Get insights for specific system areas (storage, performance, "
                "deduplication) with focused analysis and recommendations."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "focus_area": {
                        "type": "string",
                        "description": "Focus area for analysis.",
                        "enum": ["storage", "performance", "deduplication", "all"],
                        "default": "all"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_optimization_recommendations",
            "description": (
                "Get actionable optimization recommendations based on "
                "current system state."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "priority_filter": {
                        "type": "string",
                        "description": "Filter recommendations by priority level.",
                        "enum": ["high", "medium", "low", "all"],
                        "default": "all"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_predictive_insights",
            "description": (
                "[DEPRECATED] Predictive analytics is not implemented. "
                "Returns status message."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prediction_type": {
                        "type": "string",
                        "description": "Type of predictive analysis (not implemented).",
                        "enum": ["storage", "performance", "resources", "all"],
                        "default": "all"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_chunk_relationships",
            "description": (
                "Get chunk relationship statistics and analysis, or specific "
                "document context with relationship history and deduplication "
                "information."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": (
                            "Optional document ID to get specific relationship context."
                        )
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_system_health_assessment",
            "description": (
                "Get system health assessment with health scores for storage, "
                "performance, and deduplication."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "optimize_deduplication_thresholds",
            "description": (
                "Optimize deduplication thresholds automatically using advanced "
                "machine learning and performance analytics to improve "
                "system efficiency."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_domain_analysis",
            "description": (
                "Analyze documents by domain (code, text, data, documentation) "
                "to provide intelligent threshold recommendations for "
                "domain-specific deduplication."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection to analyze for domain patterns.",
                        "enum": ["short_term", "long_term"],
                        "default": "short_term"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_clustering_analysis",
            "description": (
                "Perform semantic clustering analysis on documents to identify "
                "content patterns and similarity groups for advanced "
                "deduplication insights."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection to perform clustering analysis on.",
                        "enum": ["short_term", "long_term"],
                        "default": "short_term"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_advanced_deduplication_metrics",
            "description": (
                "Get comprehensive advanced deduplication performance metrics "
                "including domain analysis, clustering effectiveness, and "
                "optimization insights."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "run_advanced_deduplication",
            "description": (
                "Run advanced deduplication with domain awareness, semantic "
                "clustering, and intelligent threshold adjustment for superior "
                "duplicate detection."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection to perform advanced deduplication on.",
                        "enum": ["short_term", "long_term"],
                        "default": "short_term"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": (
                            "If true, only analyze and report potential optimizations "
                            "without making changes."
                        ),
                        "default": False
                    }
                },
                "required": []
            }
        },
        # Document Management Tools
        {
            "name": "delete_document",
            "description": (
                "Permanently delete a document from the memory system by its ID. "
                "Requires confirmation to prevent accidental deletion."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": (
                            "The document ID to delete "
                            "(memory_id or document_id from query results)"
                        )
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": (
                            "Must be true to confirm deletion. "
                            "This action cannot be undone."
                        ),
                        "default": False
                    }
                },
                "required": ["document_id"]
            }
        },
        {
            "name": "demote_importance",
            "description": (
                "Lower a document's importance score so it will eventually expire "
                "via TTL. Use this to remove documents from permanent storage "
                "without immediate deletion."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID to demote"
                    },
                    "new_importance": {
                        "type": "number",
                        "description": (
                            "New importance score (0.0-0.94). Lower values = faster "
                            "expiry. Use 0.3 for ~1 day TTL, 0.5 for ~3 day TTL, "
                            "0.7 for ~1 week TTL."
                        ),
                        "default": 0.5,
                        "minimum": 0,
                        "maximum": 0.94
                    },
                    "reason": {
                        "type": "string",
                        "description": (
                            "Optional reason for the demotion "
                            "(stored in document metadata)"
                        )
                    }
                },
                "required": ["document_id"]
            }
        },
        {
            "name": "update_document",
            "description": (
                "Update a document's content in the memory system. Replaces the "
                "existing content while optionally preserving importance score "
                "and metadata. Use this to correct or refresh stored information."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": (
                            "The document ID to update "
                            "(memory_id or document_id from query results)"
                        )
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content for the document"
                    },
                    "metadata": {
                        "type": "object",
                        "description": (
                            "Optional metadata to merge with or replace existing. "
                            "If not provided, existing metadata is preserved."
                        ),
                        "default": {}
                    },
                    "preserve_importance": {
                        "type": "boolean",
                        "description": (
                            "If true, keep the original importance score. "
                            "If false, recalculate based on new content."
                        ),
                        "default": True
                    }
                },
                "required": ["document_id", "content"]
            }
        }
    ]
