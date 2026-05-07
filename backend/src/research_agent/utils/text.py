"""Text utilities used across the research agent."""

from __future__ import annotations


def truncate(text: str, max_chars: int = 600, suffix: str = "...") -> str:
    """Truncate text to ``max_chars`` (suffix counts toward the limit)."""
    if len(text) <= max_chars:
        return text
    available = max(0, max_chars - len(suffix))
    return text[:available] + suffix


__all__ = ["truncate"]
