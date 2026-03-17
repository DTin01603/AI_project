"""Agentic RAG Subgraph with Self-Correction.

This module assembles the five-node self-correcting RAG pipeline into a
compiled LangGraph subgraph and exposes it through the :class:`RAGSubgraph`
class.

Flow
----
::

    START
      ↓
    retrieve ──────────────────────────────────────────────────────────────────┐
      ↓                                                                        │ (retry)
    grade_documents                                                            │
      ↓ [decide_to_generate]                                                    │
      ├─ relevant docs found ──────────────────────────┐                       │
      └─ not relevant + retry budget left ─→ transform_query ─→ retrieve ─────┘
                                                                │ (retry budget exhausted)
                                                                ↓
                                                            generate (with partial context)
    generate
      ↓
    grade_generation
      ↓ [decide_after_generation_grade]
      ├─ grounded_and_useful ──────────────────→ END
      └─ hallucination | not_useful + budget left ─→ transform_query ─→ retrieve

Maximum refinement loops: MAX_RETRIES = 2 (see edges.py).
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from rag.retrieval_node import RetrievalNode
from rag.subgraph.edges import decide_after_generation_grade, decide_to_generate
from rag.subgraph.nodes import (
    generate_node,
    grade_documents_node,
    grade_generation_node,
    retrieve_node,
    transform_query_node,
)
from rag.subgraph.state import RAGSubgraphState
from research_agent.direct_llm import DirectLLM

logger = logging.getLogger(__name__)


class RAGSubgraph:
    """Self-correcting Retrieval-Augmented Generation pipeline.

    Wraps a compiled LangGraph subgraph that implements the Corrective-RAG /
    Self-RAG pattern:

    1. **retrieve** – Hybrid BM25 + vector search on document and code-file
       sources.
    2. **grade_documents** – LLM judges each retrieved passage for relevance
       to the question.
    3. **transform_query** *(conditional)* – If insufficient relevant
       documents are found, an LLM rewrites the question for a better
       retrieval pass (at most ``MAX_RETRIES`` times).
    4. **generate** – Builds a context block from the relevant passages and
       asks the LLM to produce a grounded answer.
    5. **grade_generation** – LLM verifies the answer is grounded in the
       documents and actually addresses the question; triggers another
       transform-and-retrieve loop when the answer fails.

    Usage::

        subgraph = RAGSubgraph(retrieval_node, direct_llm)
        generation, citations, meta = subgraph.run(question, history)
    """

    def __init__(
        self,
        retrieval_node: RetrievalNode,
        direct_llm: DirectLLM,
    ) -> None:
        self._retrieval_node = retrieval_node
        self._direct_llm = direct_llm
        self._compiled: Any | None = None

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build(self) -> Any:
        builder: StateGraph = StateGraph(RAGSubgraphState)

        # --- nodes ---
        builder.add_node(
            "retrieve",
            lambda s: retrieve_node(s, self._retrieval_node),
        )
        builder.add_node(
            "grade_documents",
            lambda s: grade_documents_node(s, self._direct_llm),
        )
        builder.add_node(
            "transform_query",
            lambda s: transform_query_node(s, self._direct_llm),
        )
        builder.add_node(
            "generate",
            lambda s: generate_node(s, self._direct_llm),
        )
        builder.add_node(
            "grade_generation",
            lambda s: grade_generation_node(s, self._direct_llm),
        )

        # --- edges ---
        builder.set_entry_point("retrieve")
        builder.add_edge("retrieve", "grade_documents")

        builder.add_conditional_edges(
            "grade_documents",
            decide_to_generate,
            {
                "generate": "generate",
                "transform_query": "transform_query",
            },
        )

        # Query rewrite loops back to retrieval
        builder.add_edge("transform_query", "retrieve")

        builder.add_edge("generate", "grade_generation")

        builder.add_conditional_edges(
            "grade_generation",
            decide_after_generation_grade,
            {
                "accept": END,
                "transform_query": "transform_query",
            },
        )

        return builder.compile()

    @property
    def graph(self) -> Any:
        """Lazily compiled LangGraph subgraph (singleton)."""
        if self._compiled is None:
            self._compiled = self._build()
        return self._compiled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[str], dict[str, Any]]:
        """Run the agentic RAG pipeline synchronously.

        Args:
            question: The user's question to answer.
            history:  Optional list of ``{"role": ..., "content": ...}`` dicts
                      representing prior conversation turns; passed to the
                      generate node for multi-turn context awareness.

        Returns:
            A 3-tuple ``(generation, citations, metadata)`` where:

            * **generation** – LLM answer grounded in retrieved documents.
            * **citations**  – Deduplicated source file-paths / identifiers.
            * **metadata**   – Diagnostic dict with keys:
              ``document_hits``, ``relevant_hits``, ``retry_count``,
              ``grade``.
        """
        initial_state: RAGSubgraphState = {
            "question": question,
            "history": history or [],
            "transformed_query": "",
            "documents": [],
            "relevant_documents": [],
            "generation": "",
            "citations": [],
            "retry_count": 0,
            "generation_grade": "",
        }

        try:
            result = self.graph.invoke(initial_state)
        except Exception:
            logger.exception(
                "RAGSubgraph.run failed for question: %.80s", question
            )
            return (
                "",
                [],
                {
                    "document_hits": 0,
                    "relevant_hits": 0,
                    "retry_count": 0,
                    "grade": "error",
                },
            )

        generation = result.get("generation") or ""
        citations = result.get("citations") or []
        metadata: dict[str, Any] = {
            "document_hits": len(result.get("documents") or []),
            "relevant_hits": len(result.get("relevant_documents") or []),
            "retry_count": result.get("retry_count", 0),
            "grade": result.get("generation_grade", ""),
        }
        return generation, citations, metadata
