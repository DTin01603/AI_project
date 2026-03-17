"""Node implementations for the Agentic RAG Subgraph.

Each node is a pure function that accepts the subgraph state dict and
the required dependency, then returns a partial state update.

Nodes
-----
retrieve_node          – Hybrid search against document / code-file sources.
grade_documents_node   – LLM relevance grader; filters irrelevant documents.
transform_query_node   – LLM rewrites the question for better retrieval.
generate_node          – Builds context from relevant docs + calls LLM.
grade_generation_node  – Verifies the answer is grounded and on-topic.
"""

from __future__ import annotations

import logging
from typing import Any

from rag.retrieval_node import RetrievalNode
from research_agent.direct_llm import DirectLLM
from research_agent.utils import deduplicate_list, parse_json_safe, truncate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_GRADE_DOCS_PROMPT = """\
Bạn là bộ đánh giá tài liệu. Đánh giá từng đoạn văn bên dưới có chứa thông tin \
liên quan để trả lời câu hỏi không.

Câu hỏi: {question}

Tài liệu:
{docs_text}

Trả lời CHÍNH XÁC theo định dạng JSON (không thêm bất kỳ văn bản nào khác):
{{"grades": [{{"index": 1, "relevant": true}}, {{"index": 2, "relevant": false}}, ...]}}"""

_TRANSFORM_QUERY_PROMPT = """\
Bạn là chuyên gia tối ưu hoá truy vấn tìm kiếm tài liệu kỹ thuật.

Câu hỏi gốc: {question}
Lần thử: {retry_count}

Các tài liệu tìm được trước đó không đủ liên quan. \
Hãy viết lại câu hỏi theo hướng chi tiết và kỹ thuật hơn để tìm kiếm hiệu quả \
trong cơ sở dữ liệu tài liệu nội bộ.

Chỉ trả về câu hỏi đã viết lại, không giải thích thêm."""

_GRADE_GENERATION_PROMPT = """\
Đánh giá câu trả lời AI theo hai tiêu chí:
1. Có dựa trên tài liệu được cung cấp (không bịa đặt thông tin ngoài tài liệu)
2. Có trả lời đúng câu hỏi người dùng

Câu hỏi: {question}

Tài liệu tham khảo:
{context}

Câu trả lời AI: {generation}

Trả lời CHÍNH XÁC theo JSON:
{{"grade": "grounded_and_useful", "reason": "lý do ngắn gọn"}}

Giá trị hợp lệ cho "grade": "grounded_and_useful" | "hallucination" | "not_useful"."""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_GRADES = frozenset({"grounded_and_useful", "hallucination", "not_useful"})


# ---------------------------------------------------------------------------
# Node: retrieve
# ---------------------------------------------------------------------------

def retrieve_node(
    state: dict[str, Any],
    retrieval_node: RetrievalNode,
) -> dict[str, Any]:
    """Execute hybrid retrieval against document and code-file sources."""
    query = state.get("transformed_query") or state["question"]
    try:
        docs = retrieval_node.retrieve(
            query=query,
            method="hybrid",
            top_k=5,
            min_score=0.0,
            filters={"source_types": ["document", "code_file"]},
        )
        serialized = [
            {
                "id": d.id,
                "content": d.content,
                "score": d.score,
                "source_type": d.source_type,
                "metadata": d.metadata,
            }
            for d in docs
        ]
    except Exception:
        logger.exception("rag_subgraph.retrieve_node failed")
        serialized = []
    return {"documents": serialized}


# ---------------------------------------------------------------------------
# Node: grade_documents
# ---------------------------------------------------------------------------

def grade_documents_node(
    state: dict[str, Any],
    direct_llm: DirectLLM,
) -> dict[str, Any]:
    """Grade each document for relevance; return only the relevant subset."""
    docs = state.get("documents") or []
    if not docs:
        return {"relevant_documents": []}

    question = state.get("transformed_query") or state["question"]
    docs_text = "\n\n".join(
        f"[{i + 1}] {truncate(d['content'])}" for i, d in enumerate(docs)
    )
    prompt = _GRADE_DOCS_PROMPT.format(question=question, docs_text=docs_text)

    try:
        response, _, _ = direct_llm.generate_response(
            user_message=prompt, history=[], model=None
        )
        parsed = parse_json_safe(response)
        if parsed and isinstance(parsed.get("grades"), list):
            relevant_indices = {
                g["index"] - 1  # 1-based → 0-based
                for g in parsed["grades"]
                if isinstance(g, dict) and g.get("relevant") is True
            }
            relevant_docs = [docs[i] for i in sorted(relevant_indices) if i < len(docs)]
        else:
            # Fallback: score-based threshold
            relevant_docs = [d for d in docs if d.get("score", 0) >= 0.4]
    except Exception:
        logger.exception("rag_subgraph.grade_documents_node failed")
        relevant_docs = [d for d in docs if d.get("score", 0) >= 0.4]

    return {"relevant_documents": relevant_docs}


# ---------------------------------------------------------------------------
# Node: transform_query
# ---------------------------------------------------------------------------

def transform_query_node(
    state: dict[str, Any],
    direct_llm: DirectLLM,
) -> dict[str, Any]:
    """Use LLM to rewrite the question for better document retrieval."""
    question = state["question"]
    retry_count = state.get("retry_count", 0)
    prompt = _TRANSFORM_QUERY_PROMPT.format(
        question=question, retry_count=retry_count + 1
    )
    try:
        rewritten, _, _ = direct_llm.generate_response(
            user_message=prompt, history=[], model=None
        )
        transformed = rewritten.strip() or question
    except Exception:
        logger.exception("rag_subgraph.transform_query_node failed")
        transformed = question

    return {
        "transformed_query": transformed,
        "retry_count": retry_count + 1,
    }


# ---------------------------------------------------------------------------
# Node: generate
# ---------------------------------------------------------------------------

def generate_node(
    state: dict[str, Any],
    direct_llm: DirectLLM,
) -> dict[str, Any]:
    """Generate a grounded answer from relevant context + conversation history."""
    question = state["question"]
    history = state.get("history") or []

    # Prefer graded-relevant docs; fall back to all retrieved docs
    context_docs = state.get("relevant_documents") or state.get("documents") or []

    citations: list[str] = []
    blocks: list[str] = []
    for idx, doc in enumerate(context_docs, start=1):
        meta = doc.get("metadata") or {}
        source = str(
            meta.get("file_path") or meta.get("file_name") or doc.get("id", "")
        )
        snippet = truncate(doc.get("content", "").strip(), 800)
        blocks.append(f"[{idx}] {source}\n{snippet}")
        if source:
            citations.append(source)

    augmented_question = question
    if blocks:
        context_text = "\n\n".join(blocks)
        augmented_question = (
            "Bạn được cung cấp ngữ cảnh từ tài liệu nội bộ. "
            "Ưu tiên trả lời dựa trên các đoạn này.\n\n"
            "=== NGỮ CẢNH NỘI BỘ ===\n"
            f"{context_text}\n\n"
            "=== CÂU HỎI NGƯỜI DÙNG ===\n"
            f"{question}"
        )

    try:
        generation, _, _ = direct_llm.generate_response(
            user_message=augmented_question, history=history, model=None
        )
        generation = generation or ""
    except Exception:
        logger.exception("rag_subgraph.generate_node failed")
        generation = "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời."

    # Deduplicate citations while preserving order
    unique_citations = deduplicate_list(citations)

    return {"generation": generation, "citations": unique_citations}


# ---------------------------------------------------------------------------
# Node: grade_generation
# ---------------------------------------------------------------------------

def grade_generation_node(
    state: dict[str, Any],
    direct_llm: DirectLLM,
) -> dict[str, Any]:
    """Verify the generation is grounded in context and answers the question."""
    question = state["question"]
    generation = state.get("generation") or ""
    context_docs = state.get("relevant_documents") or state.get("documents") or []

    # No documents available — cannot verify grounding; accept as-is
    if not context_docs:
        return {"generation_grade": "grounded_and_useful"}

    context = "\n\n".join(
        truncate(d.get("content", ""), 400) for d in context_docs[:3]
    )
    prompt = _GRADE_GENERATION_PROMPT.format(
        question=question,
        context=context,
        generation=truncate(generation, 600),
    )

    try:
        response, _, _ = direct_llm.generate_response(
            user_message=prompt, history=[], model=None
        )
        parsed = parse_json_safe(response)
        grade = (parsed or {}).get("grade", "grounded_and_useful")
        if grade not in _VALID_GRADES:
            grade = "grounded_and_useful"
    except Exception:
        logger.exception("rag_subgraph.grade_generation_node failed")
        grade = "grounded_and_useful"  # Fail open: accept on error

    return {"generation_grade": grade}
