"""Dense embedding search using sentence-transformers and FAISS."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.rag.chunking import Chunk

logger = logging.getLogger(__name__)


class DenseIndex:
    """Dense embedding index using sentence-transformers + FAISS."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        normalize: bool = True,
    ):
        """
        Initialize dense index.
        
        Args:
            model_name: HuggingFace model for embeddings
            normalize: Whether to L2-normalize embeddings (for cosine similarity)
        """
        self.model_name = model_name
        self.normalize = normalize
        self.model: SentenceTransformer | None = None
        self.index: faiss.IndexFlatIP | None = None  # Inner product (cosine if normalized)
        self.chunks: list[Chunk] = []
        self.dimension: int = 0
    
    def _load_model(self) -> None:
        """Lazy load embedding model."""
        if self.model is None:
            logger.info("Loading embedding model: %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
            # Use new method name with fallback
            if hasattr(self.model, 'get_embedding_dimension'):
                self.dimension = self.model.get_embedding_dimension()
            else:
                self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info("Model loaded (dimension=%d)", self.dimension)
    
    def build(self, chunks: list[Chunk], batch_size: int = 32) -> None:
        """
        Build FAISS index from chunks.
        
        Args:
            chunks: List of Chunk objects to index
            batch_size: Batch size for embedding generation
        """
        self._load_model()
        self.chunks = chunks
        
        # Generate embeddings in batches
        logger.info("Generating embeddings for %d chunks...", len(chunks))
        texts = [chunk.text for chunk in chunks]
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(chunks) > 100,
            normalize_embeddings=self.normalize,
        )
        
        # Build FAISS index (inner product for normalized vectors = cosine similarity)
        embeddings_np = np.array(embeddings).astype("float32")
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings_np)
        
        logger.info(
            "Built FAISS index with %d chunks (dim=%d, normalized=%s)",
            len(chunks),
            self.dimension,
            self.normalize,
        )
    
    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[tuple[Chunk, float]]:
        """
        Search index and return top-k chunks with similarity scores.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (Chunk, score) tuples sorted by score descending
        """
        if self.index is None or self.model is None:
            raise ValueError("Index not built. Call build() first.")
        
        # Encode query
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=self.normalize,
        )
        query_embedding_np = np.array(query_embedding).astype("float32")
        
        # Search
        scores, indices = self.index.search(query_embedding_np, top_k)
        
        results = [
            (self.chunks[idx], float(score))
            for score, idx in zip(scores[0], indices[0])
        ]
        
        logger.debug(
            "Dense search for '%s': %d results (top score: %.3f)",
            query[:50],
            len(results),
            results[0][1] if results else 0.0,
        )
        
        return results
    
    def save(self, path: Path) -> None:
        """Save index and chunks to disk."""
        path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(path / "faiss.index"))
        
        # Save chunks and metadata
        import pickle
        with (path / "chunks.pkl").open("wb") as f:
            pickle.dump(
                {
                    "chunks": self.chunks,
                    "model_name": self.model_name,
                    "normalize": self.normalize,
                    "dimension": self.dimension,
                },
                f,
            )
        
        logger.info("Saved FAISS index to %s", path)
    
    @classmethod
    def load(cls, path: Path) -> DenseIndex:
        """Load index from disk."""
        import pickle
        
        # Load metadata
        with (path / "chunks.pkl").open("rb") as f:
            state = pickle.load(f)
        
        # Create instance and load model
        index_obj = cls(
            model_name=state["model_name"],
            normalize=state["normalize"],
        )
        index_obj._load_model()
        index_obj.chunks = state["chunks"]
        index_obj.dimension = state["dimension"]
        
        # Load FAISS index
        index_obj.index = faiss.read_index(str(path / "faiss.index"))
        
        logger.info("Loaded FAISS index from %s (%d chunks)", path, len(index_obj.chunks))
        
        return index_obj
