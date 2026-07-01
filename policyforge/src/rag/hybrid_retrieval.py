"""Hybrid retrieval combining BM25 and dense search with reciprocal rank fusion."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from src.rag.bm25_search import BM25Index
from src.rag.chunking import Chunk, chunk_policy_text
from src.rag.dense_search import DenseIndex

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    results_list: list[list[tuple[Chunk, float]]],
    k: int = 60,
) -> list[tuple[Chunk, float]]:
    """
    Combine multiple ranked lists using reciprocal rank fusion (RRF).
    
    RRF formula: score = sum(1 / (k + rank_i)) across all result lists
    
    Args:
        results_list: List of ranked result lists (each is list of (chunk, score))
        k: RRF constant (higher = less emphasis on top ranks)
        
    Returns:
        Fused result list sorted by RRF score descending
    """
    chunk_scores: dict[str, float] = {}
    chunk_map: dict[str, Chunk] = {}
    
    for results in results_list:
        for rank, (chunk, _score) in enumerate(results, start=1):
            chunk_id = chunk.chunk_id
            chunk_map[chunk_id] = chunk
            
            # RRF score contribution
            rrf_score = 1.0 / (k + rank)
            chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0.0) + rrf_score
    
    # Sort by fused score
    sorted_chunks = sorted(
        chunk_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    
    return [
        (chunk_map[chunk_id], score)
        for chunk_id, score in sorted_chunks
    ]


class HybridRetriever:
    """
    Hybrid retrieval system combining BM25 (lexical) and dense embeddings (semantic).
    
    Features:
    - BM25 for exact term matching
    - Dense embeddings for semantic similarity
    - Reciprocal rank fusion for combining results
    - Section-aware chunking
    """
    
    def __init__(
        self,
        bm25_index: BM25Index,
        dense_index: DenseIndex,
        *,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5,
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            bm25_index: BM25 lexical search index
            dense_index: Dense embedding search index
            bm25_weight: Weight for BM25 results in fusion
            dense_weight: Weight for dense results in fusion
        """
        self.bm25_index = bm25_index
        self.dense_index = dense_index
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        *,
        retrieval_k: int = 20,
        fusion_method: Literal["rrf", "weighted"] = "rrf",
    ) -> list[tuple[Chunk, float]]:
        """
        Retrieve top-k most relevant chunks for query.
        
        Args:
            query: Search query
            top_k: Number of final results to return
            retrieval_k: Number of candidates to retrieve from each index
            fusion_method: How to combine results ("rrf" or "weighted")
            
        Returns:
            List of (Chunk, score) tuples sorted by relevance
        """
        # Retrieve from both indices
        bm25_results = self.bm25_index.search(query, top_k=retrieval_k)
        dense_results = self.dense_index.search(query, top_k=retrieval_k)
        
        logger.info(
            "Hybrid retrieval: BM25 found %d, dense found %d",
            len(bm25_results),
            len(dense_results),
        )
        
        # Combine results
        if fusion_method == "rrf":
            fused = reciprocal_rank_fusion([bm25_results, dense_results])
        elif fusion_method == "weighted":
            # Simple weighted combination (normalize scores first)
            bm25_max = max((s for _, s in bm25_results), default=1.0)
            dense_max = max((s for _, s in dense_results), default=1.0)
            
            chunk_scores: dict[str, float] = {}
            chunk_map: dict[str, Chunk] = {}
            
            for chunk, score in bm25_results:
                chunk_scores[chunk.chunk_id] = (
                    chunk_scores.get(chunk.chunk_id, 0.0)
                    + self.bm25_weight * (score / bm25_max)
                )
                chunk_map[chunk.chunk_id] = chunk
            
            for chunk, score in dense_results:
                chunk_scores[chunk.chunk_id] = (
                    chunk_scores.get(chunk.chunk_id, 0.0)
                    + self.dense_weight * (score / dense_max)
                )
                chunk_map[chunk.chunk_id] = chunk
            
            sorted_chunks = sorted(
                chunk_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )
            
            fused = [
                (chunk_map[chunk_id], score)
                for chunk_id, score in sorted_chunks
            ]
        else:
            raise ValueError(f"Unknown fusion_method: {fusion_method}")
        
        # Return top-k
        results = fused[:top_k]
        
        logger.info(
            "Retrieved %d chunks (fusion=%s, top score=%.3f)",
            len(results),
            fusion_method,
            results[0][1] if results else 0.0,
        )
        
        return results
    
    def retrieve_with_context(
        self,
        query: str,
        top_k: int = 5,
        **kwargs,
    ) -> tuple[list[Chunk], dict[str, float]]:
        """
        Retrieve chunks and return both chunks and retrieval metrics.
        
        Returns:
            (chunks, metrics) where metrics contains retrieval statistics
        """
        results = self.retrieve(query, top_k=top_k, **kwargs)
        
        chunks = [chunk for chunk, _score in results]
        
        metrics = {
            "num_results": len(results),
            "top_score": results[0][1] if results else 0.0,
            "mean_score": sum(s for _, s in results) / len(results) if results else 0.0,
            "unique_sections": len({c.section for c in chunks if c.section}),
        }
        
        return chunks, metrics


def build_hybrid_retriever(
    policy_text: str,
    doc_id: str,
    *,
    chunk_size: int = 512,
    overlap: int = 128,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    cache_dir: Path | None = None,
) -> HybridRetriever:
    """
    Build a hybrid retriever from policy text.
    
    Args:
        policy_text: Raw policy text
        doc_id: Document identifier (e.g., "NCD_150.3")
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks
        embedding_model: Model name for dense embeddings
        cache_dir: Directory to save/load indices (optional)
        
    Returns:
        HybridRetriever ready for queries
    """
    # Check cache
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        bm25_path = cache_dir / f"{doc_id}_bm25.pkl"
        dense_path = cache_dir / f"{doc_id}_dense"
        
        if bm25_path.exists() and dense_path.exists():
            logger.info("Loading cached indices from %s", cache_dir)
            bm25_index = BM25Index.load(bm25_path)
            dense_index = DenseIndex.load(dense_path)
            
            return HybridRetriever(bm25_index, dense_index)
    
    # Build from scratch
    logger.info("Chunking policy text (%d chars)...", len(policy_text))
    chunks = chunk_policy_text(
        policy_text,
        doc_id=doc_id,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    logger.info("Created %d chunks", len(chunks))
    
    # Build BM25 index
    logger.info("Building BM25 index...")
    bm25_index = BM25Index()
    bm25_index.build(chunks)
    
    # Build dense index
    logger.info("Building dense index (model=%s)...", embedding_model)
    dense_index = DenseIndex(model_name=embedding_model)
    dense_index.build(chunks)
    
    # Cache if requested
    if cache_dir:
        logger.info("Caching indices to %s", cache_dir)
        bm25_index.save(bm25_path)
        dense_index.save(dense_path)
    
    return HybridRetriever(bm25_index, dense_index)
