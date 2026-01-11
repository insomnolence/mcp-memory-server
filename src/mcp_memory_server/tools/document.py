

def add_document_tool(memory_system, content: str, metadata: dict = None, language: str = "text",
                      memory_type: str = "auto", context: dict = None) -> dict:
    """Add a document to the hierarchical memory system.

    Args:
        memory_system: Instance of HierarchicalMemorySystem
        content: Text content to store
        metadata: Optional metadata dictionary
        language: Programming language for chunking
        memory_type: Target collection type
        context: Optional context for importance scoring

    Returns:
        Dictionary with operation results
    """
    try:
        if metadata is None:
            metadata = {}

        # Add language to metadata
        metadata["language"] = language

        # Use hierarchical memory system
        result = memory_system.add_memory(
            content=content,
            metadata=metadata,
            context=context,
            memory_type=memory_type
        )

        return result
    except Exception as e:
        raise Exception(f"Failed to add document: {str(e)}")
