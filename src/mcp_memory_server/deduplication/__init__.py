"""
Enhanced MCP Memory Server - Deduplication Module

This module implements semantic similarity deduplication using cosine similarity
on document embeddings to reduce storage redundancy.

Based on the comprehensive deduplication proposal in docs/memory-deduplication-proposal.md
and enhanced with the system improvements from REWORK.md.

Components:
- deduplicator.py: Main deduplication logic and batch processing
- similarity.py: Cosine similarity utilities and calculations
- merger.py: Metadata merging logic and document selection

Implementation developed with assistance from Claude Code.
"""

from .deduplicator import MemoryDeduplicator
from .similarity import SimilarityCalculator
from .merger import DocumentMerger

__all__ = ['MemoryDeduplicator', 'SimilarityCalculator', 'DocumentMerger']
