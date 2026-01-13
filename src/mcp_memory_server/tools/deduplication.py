"""
Deduplication Tools for MCP Server

Implements MCP tools for memory deduplication management including
manual deduplication, statistics, and duplicate preview.
"""

import logging
from typing import Any, Dict, List
from ..server.errors import create_success_response, create_tool_error, MCPErrorCode


async def deduplicate_memories_tool(memory_system: Any, collections: str = "short_term,long_term",
                                    dry_run: bool = False) -> Dict[str, Any]:
    """Manually trigger deduplication process on specified collections.

    Args:
        memory_system: Instance of HierarchicalMemorySystem
        collections: Comma-separated collection names to deduplicate
        dry_run: If True, only analyze without making changes

    Returns:
        Dictionary with deduplication results
    """
    try:
        # Parse collections parameter
        if collections:
            collection_list = [c.strip() for c in collections.split(",")]
        else:
            collection_list = ["short_term", "long_term"]

        # Get deduplication system
        deduplicator = getattr(memory_system, 'deduplicator', None)
        if not deduplicator:
            return create_tool_error(
                "Deduplication system not initialized",
                MCPErrorCode.DEDUPLICATION_ERROR
            )

        # Process each collection
        total_results: Dict[str, Any] = {
            "success": True,
            "dry_run": dry_run,
            "collections_processed": [],
            "total_duplicates_found": 0,
            "total_documents_merged": 0,
            "processing_time": 0.0,
            "message": ""
        }

        for collection_name in collection_list:
            try:
                # Get collection
                collection = getattr(memory_system, f"{collection_name}_memory", None)
                if collection is None:
                    logging.warning(f"Collection '{collection_name}' not found")
                    continue

                # Run deduplication
                result = await deduplicator.deduplicate_collection(collection, dry_run=dry_run)

                # Aggregate results
                collection_result = {
                    "collection": collection_name,
                    "duplicates_found": result.get("duplicates_found", 0),
                    "documents_processed": result.get("documents_processed", 0),
                    "processing_time": result.get("processing_time", 0.0),
                    "message": result.get("message", "")
                }

                if not dry_run:
                    collection_result["documents_merged"] = result.get("merged_documents", 0)

                total_results["collections_processed"].append(collection_result)
                total_results["total_duplicates_found"] += result.get("duplicates_found", 0)
                total_results["total_documents_merged"] += result.get("merged_documents", 0)
                total_results["processing_time"] += result.get("processing_time", 0.0)

            except Exception as e:
                logging.error(f"Error deduplicating collection '{collection_name}': {e}")
                total_results["collections_processed"].append({
                    "collection": collection_name,
                    "error": str(e),
                    "duplicates_found": 0
                })

        # Generate summary message
        if dry_run:
            message = (f"DRY RUN: Found {total_results['total_duplicates_found']} "
                       f"potential duplicates across {len(total_results['collections_processed'])} collections")
        else:
            message = (f"Deduplication completed: {total_results['total_documents_merged']} "
                       f"documents merged from {total_results['total_duplicates_found']} duplicates")

        # Return MCP-compliant format
        return create_success_response(
            message=message,
            data={
                "dry_run": dry_run,
                "collections_processed": total_results["collections_processed"],
                "total_duplicates_found": total_results["total_duplicates_found"],
                "total_documents_merged": total_results["total_documents_merged"],
                "processing_time": total_results["processing_time"]
            }
        )

    except Exception as e:
        logging.error(f"Failed to deduplicate memories: {e}")
        return create_tool_error(
            f"Deduplication failed: {str(e)}",
            MCPErrorCode.DEDUPLICATION_ERROR,
            original_error=e
        )


def get_deduplication_stats_tool(memory_system: Any) -> Dict[str, Any]:
    """Get comprehensive deduplication statistics.

    Args:
        memory_system: Instance of HierarchicalMemorySystem

    Returns:
        Dictionary with deduplication statistics
    """
    try:
        # Get deduplication system
        deduplicator = getattr(memory_system, 'deduplicator', None)
        if not deduplicator:
            # Return MCP-compliant format when deduplication is disabled
            return {
                "total_duplicates_found": 0,
                "enabled": False,
                "message": "Deduplication system not initialized"
            }

        # Get comprehensive statistics
        if hasattr(deduplicator, 'get_deduplication_stats'):
            stats = deduplicator.get_deduplication_stats()
        elif isinstance(deduplicator, dict):
            # Handle case where deduplicator is a dict (fallback)
            stats = deduplicator
        else:
            # Fallback for unknown deduplicator types
            stats = {
                'enabled': False,
                'total_duplicates_found': 0,
                'message': 'Deduplication system not properly initialized'
            }

        # Add system health indicators
        health_score = 100.0
        if stats.get('total_duplicates_found', 0) > 100:
            health_score -= 20  # High duplicate rate indicates issues
        if not stats.get('enabled', True):
            health_score -= 50  # Disabled system

        stats['system_health_score'] = health_score

        # Add efficiency metrics
        total_processed = stats.get('total_documents_merged', 0) + stats.get('total_duplicates_found', 0)
        if total_processed > 0:
            efficiency = stats.get('total_documents_merged', 0) / total_processed * 100
            stats['deduplication_efficiency'] = round(efficiency, 2)
        else:
            stats['deduplication_efficiency'] = 0.0

        # Estimate storage savings
        if stats.get('total_documents_merged', 0) > 0:
            estimated_savings_mb = stats.get('total_storage_saved', 0) * 0.001  # Rough estimate
            stats['estimated_storage_savings_mb'] = round(estimated_savings_mb, 2)

        # Return MCP-compliant format
        return create_success_response(
            message=f"Deduplication statistics: {stats.get('total_duplicates_found', 0)} duplicates found",
            data=stats
        )

    except Exception as e:
        logging.error(f"Failed to get deduplication stats: {e}")
        return create_tool_error(
            f"Failed to get deduplication stats: {str(e)}",
            MCPErrorCode.DEDUPLICATION_ERROR,
            original_error=e
        )


async def preview_duplicates_tool(memory_system: Any, collection: str = "short_term",
                                  limit: int = 10) -> Dict[str, Any]:
    """Preview potential duplicate documents without removing them.

    Args:
        memory_system: Instance of HierarchicalMemorySystem
        collection: Collection to analyze for duplicates
        limit: Maximum number of duplicate pairs to show

    Returns:
        Dictionary with duplicate preview results
    """
    try:
        # Get deduplication system
        deduplicator = getattr(memory_system, 'deduplicator', None)
        if not deduplicator:
            return {
                "duplicates_found": 0,
                "preview_pairs": [],
                "message": "Deduplication system not initialized"
            }

        # Get collection
        target_collection = getattr(memory_system, f"{collection}_memory", None)
        if target_collection is None:
            return {
                "duplicates_found": 0,
                "preview_pairs": [],
                "message": f"Collection '{collection}' not found"
            }

        # Run preview (dry run)
        result = await deduplicator.preview_duplicates(target_collection)

        # Format results for display
        duplicates = []
        duplicate_pairs = result.get("duplicate_pairs", [])

        for i, pair in enumerate(duplicate_pairs[:limit]):
            duplicate_info = {
                "pair_id": i + 1,
                "similarity_score": round(pair.get("similarity", 0.0), 4),
                "document_1": {
                    "id": pair.get("doc1_id", "unknown"),
                    "preview": ""  # Would show content preview in full implementation
                },
                "document_2": {
                    "id": pair.get("doc2_id", "unknown"),
                    "preview": ""  # Would show content preview in full implementation
                },
                "recommended_action": pair.get("action", "merge"),
                "chosen_document": pair.get("chosen_doc", "unknown")
            }
            duplicates.append(duplicate_info)

        # Return MCP-compliant format
        return create_success_response(
            message=f"Found {len(duplicate_pairs)} potential duplicates in {collection} collection",
            data={
                "duplicates_found": len(duplicate_pairs),
                "preview_pairs": duplicates[:limit],
                "collection": collection,
                "processing_time": result.get("processing_time", 0.0)
            }
        )

    except Exception as e:
        logging.error(f"Failed to preview duplicates: {e}")
        return create_tool_error(
            f"Failed to preview duplicates: {str(e)}",
            MCPErrorCode.DEDUPLICATION_ERROR,
            original_error=e
        )
