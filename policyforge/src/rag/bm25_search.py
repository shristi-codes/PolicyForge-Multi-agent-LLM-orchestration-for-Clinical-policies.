"""BM25 lexical search implementation using rank_bm25."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from src.rag.chunking import Chunk

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25 lexical search index for policy chunks."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 index.
        
        Args:
            k1: Term frequency saturation parameter
            b: Length normalization parameter
        """
        self.k1 = k1
        self.b = b
        self.index: BM25Okapi | None = None
        self.chunks: list[Chunk] = []
        self.tokenized_corpus: list[list[str]] = []
    
    def build(self, chunks: list[Chunk]) -> None:
        """
        Build BM25 index from chunks.
        
        Args:
            chunks: List of Chunk objects to index
        """
        self.chunks = chunks
        
        # Simple whitespace tokenization (could use more sophisticated tokenizer)
        self.tokenized_corpus = [
            chunk.text.lower().split()
            for chunk in chunks
        ]
        
        self.index = BM25Okapi(
            self.tokenized_corpus,
            k1=self.k1,
            b=self.b,
        )
        
        logger.info(
            "Built BM25 index with %d chunks (k1=%.2f, b=%.2f)",
            len(chunks),
            self.k1,
            self.b,
        )
    
    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[tuple[Chunk, float]]:
        """
        Search index and return top-k chunks with scores.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (Chunk, score) tuples sorted by score descending
        """
        if self.index is None:
            raise ValueError("Index not built. Call build() first.")
        
        tokenized_query = query.lower().split()
        scores = self.index.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:top_k]
        
        results = [
            (self.chunks[i], float(scores[i]))
            for i in top_indices
        ]
        
        logger.debug(
            "BM25 search for '%s': %d results (top score: %.3f)",
            query[:50],
            len(results),
            results[0][1] if results else 0.0,
        )
        
        return results
    
    def save(self, path: Path) -> None:
        """Save index to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            "k1": self.k1,
            "b": self.b,
            "chunks": self.chunks,
            "tokenized_corpus": self.tokenized_corpus,
        }
        
        with path.open("wb") as f:
            pickle.dump(state, f)
        
        logger.info("Saved BM25 index to %s", path)
    
    @classmethod
    def load(cls, path: Path) -> BM25Index:
        """Load index from disk."""
        with path.open("rb") as f:
            state = pickle.load(f)
        
        index = cls(k1=state["k1"], b=state["b"])
        index.chunks = state["chunks"]
        index.tokenized_corpus = state["tokenized_corpus"]
        index.index = BM25Okapi(index.tokenized_corpus, k1=index.k1, b=index.b)
        
        logger.info("Loaded BM25 index from %s (%d chunks)", path, len(index.chunks))
        
        return index
