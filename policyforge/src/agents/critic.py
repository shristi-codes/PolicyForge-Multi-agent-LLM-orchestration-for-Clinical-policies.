"""Grounding validator — span citations and hallucination gate."""

from __future__ import annotations

from src.graph import PolicyForgeState


def validate(state: PolicyForgeState) -> PolicyForgeState:
    """Verify each criterion maps to a verbatim source span. TODO."""
    return state
