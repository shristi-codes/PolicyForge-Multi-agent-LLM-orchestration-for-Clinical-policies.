"""Hybrid RAG: BM25 + dense embeddings + reranking."""

from __future__ import annotations

from src.graph import PolicyForgeState


def retrieve(state: PolicyForgeState) -> PolicyForgeState:
    """Pull relevant policy clauses for extraction. TODO: implement hybrid RAG."""
    return state
