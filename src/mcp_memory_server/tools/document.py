from typing import Dict, Any, Optional


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


def legacy_add_document_tool(vectorstore, config, content: str, metadata: dict = None, language: str = "text") -> dict:
    """Legacy function that adds to the original collection for backward compatibility.
    
    Args:
        vectorstore: Legacy Chroma vectorstore instance
        config: Configuration object
        content: Text content to store
        metadata: Optional metadata dictionary
        language: Programming language for chunking
        
    Returns:
        Dictionary with operation results
    """
    import time
    from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
    from langchain_core.documents import Document
    
    try:
        embeddings_config = config.get_embeddings_config()
        chunk_size = embeddings_config.get('chunk_size', 1000)
        chunk_overlap = embeddings_config.get('chunk_overlap', 100)
        
        language_map = {
            "python": Language.PYTHON,
            "c++": Language.CPP,
            "markdown": Language.MARKDOWN,
        }
        lang_enum = language_map.get(language.lower(), None)
        
        if lang_enum:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=lang_enum, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        
        chunks = splitter.split_text(content)
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = metadata.copy() if metadata else {}
            doc_metadata.update({
                "language": language,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "timestamp": time.time(),
                "collection_type": "legacy"
            })
            documents.append(Document(page_content=chunk, metadata=doc_metadata))
        
        vectorstore.add_documents(documents)
        
        return {
            "success": True,
            "message": f"Added {len(documents)} document chunks to legacy collection.",
            "chunks_added": len(documents)
        }
    except Exception as e:
        raise Exception(f"Failed to add document to legacy collection: {str(e)}")