"""
Cosine Similarity Utilities for Document Deduplication

Implements efficient cosine similarity calculations for document embeddings
using scikit-learn for batch processing.

Based on the algorithm from docs/memory-deduplication-proposal.md
"""

import time
import numpy as np
import logging
from typing import List, Tuple, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity


class SimilarityCalculator:
    """Efficient cosine similarity calculator for document deduplication."""

    def __init__(self, similarity_threshold: float = 0.95):
        """Initialize similarity calculator.

        Args:
            similarity_threshold: Threshold above which documents are considered duplicates
        """
        self.similarity_threshold = similarity_threshold
        self.calculation_cache: Dict[str, float] = {}

    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First document embedding
            embedding2: Second document embedding

        Returns:
            Cosine similarity score (0-1)
        """
        # Reshape embeddings for sklearn
        emb1 = np.array(embedding1).reshape(1, -1)
        emb2 = np.array(embedding2).reshape(1, -1)

        # Calculate cosine similarity
        similarity = cosine_similarity(emb1, emb2)[0][0]
        return float(similarity)

    def find_duplicates_batch(self, documents: List[Dict[str, Any]],
                              threshold: Optional[float] = None) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
        """Find duplicate documents using batch similarity calculation.

        This is the core algorithm from the existing deduplication proposal.

        Args:
            documents: List of document dictionaries with embeddings
            threshold: Similarity threshold (uses instance default if None)

        Returns:
            List of tuples: (doc1, doc2, similarity_score)
        """
        if threshold is None:
            threshold = self.similarity_threshold

        if len(documents) < 2:
            return []

        start_time = time.time()

        # Extract embeddings for batch processing
        embeddings = []
        valid_docs = []

        for doc in documents:
            embedding = doc.get('embedding')
            if embedding is not None:
                embeddings.append(embedding)
                valid_docs.append(doc)

        if len(embeddings) < 2:
            logging.warning("Not enough documents with embeddings for deduplication")
            return []

        # Convert to numpy array for efficient computation
        embeddings_array = np.array(embeddings)

        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(embeddings_array)

        # Find duplicates above threshold
        duplicates = []
        for i in range(len(valid_docs)):
            for j in range(i + 1, len(valid_docs)):
                similarity_score = similarity_matrix[i][j]
                if similarity_score > threshold:
                    duplicates.append((
                        valid_docs[i],
                        valid_docs[j],
                        float(similarity_score)
                    ))

        processing_time = time.time() - start_time
        logging.info(f"Batch similarity calculation completed: {len(duplicates)} duplicates found "
                     f"from {len(valid_docs)} documents in {processing_time:.2f}s")

        return duplicates

    def find_similar_candidates(self, target_embedding: np.ndarray,
                                candidate_embeddings: List[np.ndarray],
                                top_k: int = 5) -> List[Tuple[int, float]]:
        """Find most similar candidates for ingestion-time duplicate checking.

        Args:
            target_embedding: Embedding of new document to check
            candidate_embeddings: List of existing document embeddings
            top_k: Number of top similar candidates to return

        Returns:
            List of tuples: (candidate_index, similarity_score)
        """
        if not candidate_embeddings:
            return []

        target_emb = np.array(target_embedding).reshape(1, -1)
        candidates_array = np.array(candidate_embeddings)

        # Calculate similarities with all candidates
        similarities = cosine_similarity(target_emb, candidates_array)[0]

        # Get top-k most similar
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            similarity_score = float(similarities[idx])
            if similarity_score > self.similarity_threshold:
                results.append((int(idx), similarity_score))

        return results

    def cluster_similar_documents(self, documents: List[Dict[str, Any]],
                                  cluster_threshold: float = 0.85) -> List[List[Dict[str, Any]]]:
        """Group documents into similarity clusters for enhanced cleanup.

        Args:
            documents: List of document dictionaries with embeddings
            cluster_threshold: Threshold for grouping into clusters

        Returns:
            List of document clusters (lists of similar documents)
        """
        if len(documents) < 2:
            return [[doc] for doc in documents]

        # Extract embeddings
        embeddings = []
        valid_docs = []

        for doc in documents:
            embedding = doc.get('embedding')
            if embedding is not None:
                embeddings.append(embedding)
                valid_docs.append(doc)

        if len(embeddings) < 2:
            return [[doc] for doc in valid_docs]

        # Calculate similarity matrix
        embeddings_array = np.array(embeddings)
        similarity_matrix = cosine_similarity(embeddings_array)

        # Simple clustering based on similarity threshold
        clusters = []
        assigned = set()

        for i in range(len(valid_docs)):
            if i in assigned:
                continue

            # Start new cluster
            cluster = [valid_docs[i]]
            assigned.add(i)

            # Find all similar documents
            for j in range(i + 1, len(valid_docs)):
                if j not in assigned and similarity_matrix[i][j] > cluster_threshold:
                    cluster.append(valid_docs[j])
                    assigned.add(j)

            clusters.append(cluster)

        logging.info(f"Document clustering completed: {len(clusters)} clusters from {len(valid_docs)} documents")
        return clusters

    def get_similarity_stats(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about document similarity distribution.

        Args:
            documents: List of document dictionaries with embeddings

        Returns:
            Dictionary with similarity statistics
        """
        if len(documents) < 2:
            return {
                'total_documents': len(documents),
                'similarity_pairs': 0,
                'mean_similarity': 0.0,
                'max_similarity': 0.0,
                'potential_duplicates': 0
            }

        # Calculate all pairwise similarities
        similarities = []
        duplicate_count = 0

        for i in range(len(documents)):
            for j in range(i + 1, len(documents)):
                emb1 = documents[i].get('embedding')
                emb2 = documents[j].get('embedding')

                if emb1 is not None and emb2 is not None:
                    sim = self.calculate_similarity(emb1, emb2)
                    similarities.append(sim)
                    if sim > self.similarity_threshold:
                        duplicate_count += 1

        if not similarities:
            return {
                'total_documents': len(documents),
                'similarity_pairs': 0,
                'mean_similarity': 0.0,
                'max_similarity': 0.0,
                'potential_duplicates': 0
            }

        return {
            'total_documents': len(documents),
            'similarity_pairs': len(similarities),
            'mean_similarity': float(np.mean(similarities)),
            'max_similarity': float(np.max(similarities)),
            'min_similarity': float(np.min(similarities)),
            'std_similarity': float(np.std(similarities)),
            'potential_duplicates': duplicate_count,
            'duplication_rate': duplicate_count / len(similarities) if similarities else 0.0
        }
