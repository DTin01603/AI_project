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
    """Execute hybrid retrieval via rag.retrieve skill."""
    query = state.get("transformed_query") or state["question"]
    try:
        skill = get_registry().get("rag.retrieve")
        # Inject retrieval_node if not already injected
        if skill.retrieval_node is None:
            skill.retrieval_node = retrieval_node
        out = skill.invoke({"query": query})
        return {"documents": out["documents"]}
    except SkillNotFoundError:
        logger.warning("rag.retrieve skill not found — using RetrievalNode directly")
        try:
            docs = retrieval_node.retrieve(
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
    """Grade each document for relevance via rag.grade_documents skill."""
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
        return {"relevant_documents": [d for d in docs if d.get("score", 0) >= 0.4]}
    except Exception:
        logger.exception("grade_documents_node failed")
        return {"relevant_documents": [d for d in docs if d.get("score", 0) >= 0.4]}


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
    """Verify the generation via rag.grade_generation skill."""
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
        return {"generation_grade": "grounded_and_useful"}
    except Exception:
        logger.exception("grade_generation_node failed")
        return {"generation_grade": "grounded_and_useful"}
