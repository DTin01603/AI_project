"""Conditional edge functions for the Agentic RAG Subgraph."""

from __future__ import annotations

from typing import Any

MAX_RETRIES: int = 2
"""Maximum number of query-transformation retries before forcing generation."""


def decide_to_generate(state: dict[str, Any]) -> str:
    """Decide whether to generate an answer or rewrite the query.

    Called after grade_documents.

    - If at least one relevant document was found → proceed to "generate".
    - Else if the retry budget is not exhausted → "transform_query" for a
      better retrieval attempt.
    - Else → "generate" anyway with whatever context is available (graceful
      degradation so the user always gets a response).
    """
    relevant = state.get("relevant_documents") or []
    retry_count = state.get("retry_count", 0)

    if len(relevant) >= 1:
        return "generate"
    if retry_count < MAX_RETRIES:
        return "transform_query"
    return "generate"  # Exhausted retries — generate with partial context


def decide_after_generation_grade(state: dict[str, Any]) -> str:
    """Decide whether to accept the generation or attempt self-correction.

    Called after grade_generation.

    - "grounded_and_useful" → "accept" (→ END).
    - Otherwise, if retry budget remains → "transform_query" to retrieve
      better context and regenerate.
    - If retry budget is exhausted → "accept" to avoid an infinite loop.
    """
    grade = state.get("generation_grade", "grounded_and_useful")
    retry_count = state.get("retry_count", 0)

    if grade == "grounded_and_useful":
        return "accept"
    if retry_count < MAX_RETRIES:
        return "transform_query"
    return "accept"  # Give up after max retries — return what we have
