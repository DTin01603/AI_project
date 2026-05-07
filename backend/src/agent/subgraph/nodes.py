"""Node implementations for the Agentic RAG Subgraph.

Each node is a thin wrapper around a skill:
- retrieve_node         → rag.retrieve
- grade_documents_node  → rag.grade_documents
- transform_query_node  → rag.transform_query
- generate_node         → rag.answer_with_context
- grade_generation_node → rag.grade_generation
"""

from __future__ import annotations

import logging
from typing import Any

from agent.nodes.retrieval_node import RetrievalNode
from skills import SkillNotFoundError, get_registry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node: retrieve
# ---------------------------------------------------------------------------

def retrieve_node(
    state: dict[str, Any],
    retrieval_node: RetrievalNode,
) -> dict[str, Any]:
    """Execute hybrid retrieval via rag.retrieve skill.

    The skill needs the underlying ``RetrievalService`` (not the LangGraph
    adapter), so we pull it off the node when wiring the registry. The node
    is still passed in because graph construction already injects it.
    """
    query = state.get("transformed_query") or state["question"]
    service = retrieval_node.service
    try:
        skill = get_registry().get("rag.retrieve")
        if skill.service is None:
            skill.service = service
        out = skill.invoke({"query": query})
        return {"documents": out["documents"]}
    except SkillNotFoundError:
        logger.warning("rag.retrieve skill not found — using RetrievalService directly")
        try:
            docs = service.retrieve(
                query=query,
                method="hybrid",
                top_k=8,
                min_score=0.0,
                filters={"source_types": ["document", "code_file"]},
            )
            return {"documents": [
                {"id": d.id, "content": d.content, "score": d.score,
                 "source_type": d.source_type, "metadata": d.metadata}
                for d in docs
            ]}
        except Exception:
            logger.exception("retrieve_node fallback path failed")
            return {"documents": []}
    except Exception:
        logger.exception("retrieve_node failed")
        return {"documents": []}


# ---------------------------------------------------------------------------
# Node: grade_documents
# ---------------------------------------------------------------------------

def grade_documents_node(state: dict[str, Any]) -> dict[str, Any]:
    """Grade each document for relevance via rag.grade_documents skill.

    Fallback policy on grader failure: keep documents whose retrieval score
    clears a threshold. This is a heuristic, not a silent pass — the
    ``grade_fallback_used`` flag records that the LLM grader was bypassed.
    """
    docs = state.get("documents") or []
    if not docs:
        return {"relevant_documents": []}
    question = state.get("transformed_query") or state["question"]
    model = state.get("model")
    try:
        out = get_registry().get("rag.grade_documents").invoke(
            {"question": question, "documents": docs},
            model_override=model,
        )
        return {"relevant_documents": out["relevant_documents"]}
    except SkillNotFoundError:
        logger.warning("rag.grade_documents skill not registered — falling back to score threshold")
        return {
            "relevant_documents": [d for d in docs if d.get("score", 0) >= 0.4],
            "grade_fallback_used": True,
        }
    except Exception:
        logger.exception("grade_documents_node failed — falling back to score threshold")
        return {
            "relevant_documents": [d for d in docs if d.get("score", 0) >= 0.4],
            "grade_fallback_used": True,
        }


# ---------------------------------------------------------------------------
# Node: transform_query
# ---------------------------------------------------------------------------

def transform_query_node(state: dict[str, Any]) -> dict[str, Any]:
    """Rewrite the question via rag.transform_query skill."""
    question = state["question"]
    history = state.get("history") or []
    retry_count = state.get("retry_count", 0)
    model = state.get("model")
    try:
        out = get_registry().get("rag.transform_query").invoke(
            {
                "question": question,
                "history": history,
                "retry_count": retry_count + 1,
            },
            model_override=model,
        )
        transformed = out["transformed_query"] or question
    except SkillNotFoundError:
        transformed = question
    except Exception:
        logger.exception("transform_query_node failed")
        transformed = question

    return {"transformed_query": transformed, "retry_count": retry_count + 1}


# ---------------------------------------------------------------------------
# Node: generate
# ---------------------------------------------------------------------------

def generate_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate answer from context via rag.answer_with_context skill."""
    question = state["question"]
    history = state.get("history") or []
    context_docs = state.get("relevant_documents") or state.get("documents") or []
    model = state.get("model")

    try:
        out = get_registry().get("rag.answer_with_context").invoke(
            {"question": question, "history": history, "relevant_documents": context_docs},
            model_override=model,
        )
        return {"generation": out["generation"], "citations": out["citations"]}
    except SkillNotFoundError:
        return {"generation": "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời.", "citations": []}
    except Exception:
        logger.exception("generate_node failed")
        return {"generation": "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời.", "citations": []}


# ---------------------------------------------------------------------------
# Node: grade_generation
# ---------------------------------------------------------------------------

def grade_generation_node(state: dict[str, Any]) -> dict[str, Any]:
    """Verify the generation via rag.grade_generation skill.

    Fallback policy on grader failure: return ``"not_useful"`` rather than
    silently accepting. The retry loop in ``decide_after_generation_grade``
    will then either retry with a transformed query or — if the budget is
    exhausted — accept the answer with ``grade_fallback_used`` recorded so
    the silent-pass is observable downstream.
    """
    question = state["question"]
    generation = state.get("generation") or ""
    context_docs = state.get("relevant_documents") or state.get("documents") or []
    model = state.get("model")

    try:
        out = get_registry().get("rag.grade_generation").invoke(
            {"question": question, "generation": generation, "context_docs": context_docs},
            model_override=model,
        )
        return {"generation_grade": out["grade"]}
    except SkillNotFoundError:
        logger.warning("rag.grade_generation skill not registered — defaulting to not_useful")
        return {"generation_grade": "not_useful", "grade_fallback_used": True}
    except Exception:
        logger.exception("grade_generation_node failed — defaulting to not_useful")
        return {"generation_grade": "not_useful", "grade_fallback_used": True}
