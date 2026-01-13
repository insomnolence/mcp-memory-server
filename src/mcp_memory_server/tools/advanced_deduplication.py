"""
Advanced Deduplication Tools for MCP Server

Provides tools for accessing advanced deduplication features including
domain analysis, semantic clustering, threshold optimization, and performance metrics.
"""

import asyncio
import logging
from typing import Any, Dict
from ..server.errors import create_success_response, create_tool_error, MCPErrorCode


def optimize_deduplication_thresholds_tool(memory_system: Any) -> Dict[str, Any]:
    """Optimize deduplication thresholds automatically using advanced features.

    Args:
        memory_system: Instance of HierarchicalMemorySystem

    Returns:
        Dictionary with threshold optimization results
    """
    try:
        if not hasattr(memory_system, 'deduplicator') or not memory_system.deduplicator:
            return create_tool_error(
                "Deduplication system not available",
                MCPErrorCode.DEDUPLICATION_ERROR
            )

        if not hasattr(memory_system.deduplicator, 'advanced_features'):
            return create_tool_error(
                "Advanced deduplication features not enabled",
                MCPErrorCode.CONFIGURATION_ERROR
            )

        optimization_results = memory_system.deduplicator.optimize_thresholds()

        # Return MCP-compliant format
        return create_success_response(
            message="Threshold optimization completed successfully",
            data={"optimization_result": optimization_results}
        )

    except Exception as e:
        logging.error(f"Failed to optimize thresholds: {e}")
        return create_tool_error(
            f"Failed to optimize thresholds: {str(e)}",
            MCPErrorCode.DEDUPLICATION_ERROR,
            original_error=e
        )


async def get_domain_analysis_tool(memory_system: Any, collection: str = "short_term") -> Dict[str, Any]:
    """Analyze documents by domain for deduplication threshold recommendations.

    Args:
        memory_system: Instance of HierarchicalMemorySystem
        collection: Collection to analyze ('short_term' or 'long_term')

    Returns:
        Dictionary with domain analysis results
    """
    try:
        if not hasattr(memory_system, 'deduplicator') or not memory_system.deduplicator:
            return create_tool_error(
                "Deduplication system not available",
                MCPErrorCode.DEDUPLICATION_ERROR
            )

        if not hasattr(memory_system.deduplicator, 'advanced_features'):
            return create_tool_error(
                "Advanced deduplication features not enabled",
                MCPErrorCode.CONFIGURATION_ERROR
            )

        # Get documents from the specified collection
        try:
            chroma_collection = getattr(memory_system, f"{collection}_memory", None)
            if not chroma_collection:
                return create_tool_error(
                    f"Collection '{collection}' not found",
                    MCPErrorCode.VALIDATION_ERROR,
                    additional_data={"collection": collection}
                )

            # Get sample of documents for analysis
            all_docs = await asyncio.to_thread(chroma_collection.similarity_search, "", k=1000)  # Sample for analysis

            if not all_docs:
                return create_tool_error(
                    f"No documents found in collection '{collection}'",
                    MCPErrorCode.MEMORY_SYSTEM_ERROR,
                    additional_data={"collection": collection}
                )

            # Convert to format expected by domain analysis
            doc_dicts = []
            for doc in all_docs[:100]:  # Limit for performance
                doc_dict = {
                    'id': doc.metadata.get('chunk_id', str(hash(doc.page_content))),
                    'page_content': doc.page_content,
                    'metadata': doc.metadata
                }
                doc_dicts.append(doc_dict)

            domain_analysis = memory_system.deduplicator.get_domain_analysis(doc_dicts)
            domain_analysis['collection_analyzed'] = collection
            domain_analysis['sample_size'] = len(doc_dicts)

            # Return MCP-compliant format
            return create_success_response(
                message=f"Domain analysis completed for {len(doc_dicts)} documents from {collection}",
                data={"analysis_result": domain_analysis}
            )

        except Exception as e:
            return create_tool_error(
                f"Failed to access collection '{collection}': {str(e)}",
                MCPErrorCode.MEMORY_SYSTEM_ERROR,
                original_error=e
            )

    except Exception as e:
        logging.error(f"Failed to get domain analysis: {e}")
        return create_tool_error(
            f"Failed to get domain analysis: {str(e)}",
            MCPErrorCode.DEDUPLICATION_ERROR,
            original_error=e
        )


async def get_clustering_analysis_tool(memory_system: Any, collection: str = "short_term") -> Dict[str, Any]:
    """Perform semantic clustering analysis on documents.

    Args:
        memory_system: Instance of HierarchicalMemorySystem
        collection: Collection to analyze ('short_term' or 'long_term')

    Returns:
        Dictionary with clustering analysis results
    """
    try:
        if not hasattr(memory_system, 'deduplicator') or not memory_system.deduplicator:
            return create_tool_error(
                "Deduplication system not available",
                MCPErrorCode.DEDUPLICATION_ERROR
            )

        if not hasattr(memory_system.deduplicator, 'advanced_features'):
            return create_tool_error(
                "Advanced deduplication features not enabled",
                MCPErrorCode.CONFIGURATION_ERROR
            )

        # Get documents from the specified collection
        try:
            chroma_collection = getattr(memory_system, f"{collection}_memory", None)
            if not chroma_collection:
                return create_tool_error(
                    f"Collection '{collection}' not found",
                    MCPErrorCode.VALIDATION_ERROR,
                    additional_data={"collection": collection}
                )

            # Get sample of documents for analysis
            all_docs = await asyncio.to_thread(chroma_collection.similarity_search, "", k=500)  # Sample for clustering

            if not all_docs:
                return create_tool_error(
                    f"No documents found in collection '{collection}'",
                    MCPErrorCode.MEMORY_SYSTEM_ERROR,
                    additional_data={"collection": collection}
                )

            # Convert to format expected by clustering analysis
            doc_dicts = []
            for doc in all_docs[:50]:  # Limit for performance (clustering is expensive)
                doc_dict = {
                    'id': doc.metadata.get('chunk_id', str(hash(doc.page_content))),
                    'page_content': doc.page_content,
                    'metadata': doc.metadata
                }
                doc_dicts.append(doc_dict)

            clustering_analysis = memory_system.deduplicator.get_clustering_analysis(doc_dicts)
            clustering_analysis['collection_analyzed'] = collection
            clustering_analysis['sample_size'] = len(doc_dicts)

            # Return MCP-compliant format
            return create_success_response(
                message=f"Clustering analysis completed for {len(doc_dicts)} documents from {collection}",
                data={"analysis_result": clustering_analysis}
            )

        except Exception as e:
            return create_tool_error(
                f"Failed to access collection '{collection}': {str(e)}",
                MCPErrorCode.MEMORY_SYSTEM_ERROR,
                original_error=e
            )

    except Exception as e:
        logging.error(f"Failed to get clustering analysis: {e}")
        return create_tool_error(
            f"Failed to get clustering analysis: {str(e)}",
            MCPErrorCode.DEDUPLICATION_ERROR,
            original_error=e
        )


def get_advanced_deduplication_metrics_tool(memory_system: Any) -> Dict[str, Any]:
    """Get comprehensive advanced deduplication performance metrics.

    Args:
        memory_system: Instance of HierarchicalMemorySystem

    Returns:
        Dictionary with advanced performance metrics
    """
    try:
        if not hasattr(memory_system, 'deduplicator') or not memory_system.deduplicator:
            return create_tool_error(
                "Deduplication system not available",
                MCPErrorCode.DEDUPLICATION_ERROR
            )

        if not hasattr(memory_system.deduplicator, 'advanced_features'):
            return create_tool_error(
                "Advanced deduplication features not enabled",
                MCPErrorCode.CONFIGURATION_ERROR
            )

        # Get comprehensive metrics
        advanced_metrics = memory_system.deduplicator.get_advanced_performance_metrics()
        basic_stats = memory_system.deduplicator.get_deduplication_stats()

        comprehensive_metrics = {
            'advanced_features': advanced_metrics,
            'basic_deduplication_stats': basic_stats,
            'features_enabled': {
                'domain_awareness': True,
                'semantic_clustering': advanced_metrics.get('clustering_enabled', False),
                'threshold_optimization': advanced_metrics.get('optimization_enabled', False)
            }
        }

        # Return MCP-compliant format
        return create_success_response(
            message="Advanced deduplication metrics retrieved successfully",
            data={"metrics": comprehensive_metrics}
        )

    except Exception as e:
        logging.error(f"Failed to get advanced deduplication metrics: {e}")
        return create_tool_error(
            f"Failed to get advanced deduplication metrics: {str(e)}",
            MCPErrorCode.DEDUPLICATION_ERROR,
            original_error=e
        )


async def run_advanced_deduplication_tool(memory_system: Any, collection: str = "short_term",
                                          dry_run: bool = False) -> Dict[str, Any]:
    """Run advanced deduplication with domain awareness and semantic clustering.

    Args:
        memory_system: Instance of HierarchicalMemorySystem
        collection: Collection to deduplicate ('short_term' or 'long_term')
        dry_run: If true, only analyze without making changes

    Returns:
        Dictionary with advanced deduplication results
    """
    try:
        if not hasattr(memory_system, 'deduplicator') or not memory_system.deduplicator:
            return create_tool_error(
                "Deduplication system not available",
                MCPErrorCode.DEDUPLICATION_ERROR
            )

        if not hasattr(memory_system.deduplicator, 'advanced_features'):
            return create_tool_error(
                "Advanced deduplication features not enabled",
                MCPErrorCode.CONFIGURATION_ERROR
            )

        # Get the specified collection
        try:
            chroma_collection = getattr(memory_system, f"{collection}_memory", None)
            if not chroma_collection:
                return create_tool_error(
                    f"Collection '{collection}' not found",
                    MCPErrorCode.VALIDATION_ERROR,
                    additional_data={"collection": collection}
                )

            # Run advanced deduplication
            results = await memory_system.deduplicator.deduplicate_collection(chroma_collection, dry_run=dry_run)
            results['collection'] = collection
            results['advanced_features_used'] = True

            # Return MCP-compliant format
            return create_success_response(
                message=f"Advanced deduplication {'analysis' if dry_run else 'execution'} completed for {collection}",
                data={"result": results}
            )

        except Exception as e:
            return create_tool_error(
                f"Failed to access collection '{collection}': {str(e)}",
                MCPErrorCode.MEMORY_SYSTEM_ERROR,
                original_error=e
            )

    except Exception as e:
        logging.error(f"Failed to run advanced deduplication: {e}")
        return create_tool_error(
            f"Failed to run advanced deduplication: {str(e)}",
            MCPErrorCode.DEDUPLICATION_ERROR,
            original_error=e
        )
