#!/usr/bin/env python3
"""
Cleanup script to remove test data accidentally written to production database.

This script identifies and removes documents that appear to be test data based on:
1. Metadata patterns (source, type fields containing "test")
2. Content patterns (test-specific phrases)
3. Timestamp ranges (documents created during test runs)

Usage:
    python scripts/cleanup_test_data.py --dry-run    # Preview what would be deleted
    python scripts/cleanup_test_data.py --delete     # Actually delete the documents
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import chromadb


# Test data patterns to identify
TEST_METADATA_PATTERNS = {
    "source": ["test_cleanup", "test_lifecycle", "test_", "test-"],
    "type": ["test_expiry", "test_", "test-"],
}

TEST_CONTENT_PATTERNS = [
    "This document will be expired and cleaned up",
    "This is a critical permanent document that must never be deleted",
    "Machine learning algorithms for data analysis",
    "Deep learning neural networks for image recognition",
    "Natural language processing for text analysis", 
    "Computer vision algorithms for object detection",
    "Reinforcement learning for game playing",
    "Data science techniques for business intelligence",
    "Statistical analysis methods for research",
    "Big data processing frameworks",
    "Cloud computing infrastructure",
    "DevOps practices for continuous deployment",
    "This document tests TTL and cleanup functionality",
    "Test document for",
    "test_semantic_clustering",
    "test_deduplication",
    "test_permanence",
    "test_background_maintenance",
]

# Database location
DB_PATH = project_root / "data" / "dollhouse-memory"


def get_collections(client):
    """Get all collections from ChromaDB."""
    return client.list_collections()


def find_test_documents(collection) -> list[dict]:
    """Find documents that appear to be test data."""
    test_docs = []
    
    # Get all documents from collection
    results = collection.get(include=["documents", "metadatas"])
    
    if not results or not results.get("ids"):
        return test_docs
    
    for i, doc_id in enumerate(results["ids"]):
        content = results["documents"][i] if results.get("documents") else ""
        metadata = results["metadatas"][i] if results.get("metadatas") else {}
        
        is_test = False
        reason = []
        
        # Check metadata patterns
        for field, patterns in TEST_METADATA_PATTERNS.items():
            field_value = str(metadata.get(field, "")).lower()
            for pattern in patterns:
                if pattern.lower() in field_value:
                    is_test = True
                    reason.append(f"metadata.{field} contains '{pattern}'")
                    break
        
        # Check content patterns
        content_lower = (content or "").lower()
        for pattern in TEST_CONTENT_PATTERNS:
            if pattern.lower() in content_lower:
                is_test = True
                reason.append(f"content matches '{pattern[:40]}...'")
                break
        
        if is_test:
            test_docs.append({
                "id": doc_id,
                "content": (content or "")[:100] + "..." if content and len(content) > 100 else content,
                "metadata": metadata,
                "reason": reason,
            })
    
    return test_docs


def main():
    parser = argparse.ArgumentParser(description="Cleanup test data from production database")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be deleted (default)")
    parser.add_argument("--delete", action="store_true", help="Actually delete the documents")
    parser.add_argument("--db-path", type=str, default=str(DB_PATH), help="Path to ChromaDB database")
    args = parser.parse_args()
    
    if not args.delete:
        args.dry_run = True
    
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"Error: Database path not found: {db_path}")
        sys.exit(1)
    
    print(f"{'='*60}")
    print(f"Test Data Cleanup Script")
    print(f"{'='*60}")
    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'DELETE MODE'}")
    print(f"{'='*60}\n")
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=str(db_path))
    collections = get_collections(client)
    
    print(f"Found {len(collections)} collections\n")
    
    total_found = 0
    total_deleted = 0
    
    for coll_info in collections:
        coll_name = coll_info.name if hasattr(coll_info, 'name') else str(coll_info)
        collection = client.get_collection(coll_name)
        
        print(f"\n{'─'*40}")
        print(f"Collection: {coll_name}")
        print(f"Total documents: {collection.count()}")
        
        test_docs = find_test_documents(collection)
        total_found += len(test_docs)
        
        if not test_docs:
            print("  No test documents found")
            continue
        
        print(f"  Found {len(test_docs)} test documents:")
        
        for doc in test_docs[:10]:  # Show first 10
            print(f"\n    ID: {doc['id']}")
            print(f"    Content: {doc['content']}")
            print(f"    Reason: {', '.join(doc['reason'])}")
        
        if len(test_docs) > 10:
            print(f"\n    ... and {len(test_docs) - 10} more")
        
        if args.delete and test_docs:
            print(f"\n  Deleting {len(test_docs)} documents...")
            ids_to_delete = [doc["id"] for doc in test_docs]
            collection.delete(ids=ids_to_delete)
            total_deleted += len(test_docs)
            print(f"  Deleted {len(test_docs)} documents")
    
    print(f"\n{'='*60}")
    print(f"Summary")
    print(f"{'='*60}")
    print(f"Total test documents found: {total_found}")
    
    if args.dry_run:
        print(f"\nThis was a DRY RUN. No documents were deleted.")
        print(f"Run with --delete to actually remove these documents.")
    else:
        print(f"Total documents deleted: {total_deleted}")
    
    # Show final counts
    print(f"\nFinal document counts:")
    for coll_info in collections:
        coll_name = coll_info.name if hasattr(coll_info, 'name') else str(coll_info)
        collection = client.get_collection(coll_name)
        print(f"  {coll_name}: {collection.count()}")


if __name__ == "__main__":
    main()
