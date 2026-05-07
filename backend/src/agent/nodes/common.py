from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Any

from agent.nodes.retrieval_node import RetrievalNode
from agent.database import Database
from agent.state import AgentState
from agent.utils import get_execution_metadata, update_node_timing
from agent.utils.model_runtime import resolve_and_apply_model
from agent.utils.text import truncate
from skills import get_registry

if TYPE_CHECKING:
    from agent.subgraph import RAGSubgraph


def extract_last_message_content(state: AgentState) -> str:
    messages = state.get("messages") or []
    if not messages:
        return ""
    content = getattr(messages[-1], "content", "")
    return content if isinstance(content, str) else str(content)


def _prepare_document_context(retrieval_node: RetrievalNode, question: str) -> tuple[str, list[str], dict[str, Any]]:
    retrieved = retrieval_node.retrieve(
        query=question,
        method="hybrid",
        top_k=3,
        min_score=0.0,
        filters={"source_types": ["document", "code_file"]},
    )

    if not retrieved:
        return "", [], {"document_hits": 0}

    blocks: list[str] = []
    citations: list[str] = []
    for idx, doc in enumerate(retrieved, start=1):
        file_path = str(doc.metadata.get("file_path") or doc.metadata.get("file_name") or doc.id)
        snippet = doc.content.strip()
        snippet = truncate(snippet, max_chars=800)
        blocks.append(f"[{idx}] {file_path}\n{snippet}")
        citations.append(file_path)

    context_prompt = (
        "Ban duoc cung cap ngu canh truy xuat tu tai lieu noi bo. "
        "Neu ngu canh phu hop, uu tien tra loi dua tren cac doan nay.\n\n"
        "=== NGU CANH NOI BO ===\n"
        + "\n\n".join(blocks)
    )
    return context_prompt, citations, {"document_hits": len(retrieved)}


def run_llm_node(
    state: AgentState,
    database: Database,
    retrieval_node: RetrievalNode | None = None,
    *,
    node_name: str,
    fallback_answer: str,
    rag_subgraph: "RAGSubgraph | None" = None,
) -> dict[str, Any]:
    started = perf_counter()
    question = extract_last_message_content(state)

    metadata = get_execution_metadata(state)
    model = resolve_and_apply_model(metadata)
    conversation_id = metadata.get("conversation_id")
    if not conversation_id:
        conversation_id = database.create_conversation()
        metadata["conversation_id"] = conversation_id

    citations = list(state.get("citations") or [])

    try:
        history = database.get_conversation_history(conversation_id)

        if rag_subgraph is not None:
            generation, retrieved_citations, retrieval_meta = rag_subgraph.run(
                question, history, model=model
            )
            answer = generation or fallback_answer
            provider = "rag_subgraph"
            finish_reason = "stop"
        elif retrieval_node is not None:
            context_prompt, retrieved_citations, retrieval_meta = _prepare_document_context(
                retrieval_node, question
            )
            augmented_question = question
            if context_prompt:
                augmented_question = f"{context_prompt}\n\n=== CAU HOI NGUOI DUNG ===\n{question}"
            skill_result = get_registry().get("direct_answer").invoke(
                {"user_message": augmented_question, "history": history},
                model_override=model,
            )
            answer = skill_result["answer"]
            provider = skill_result["provider"]
            finish_reason = skill_result["finish_reason"]
        else:
            # Pure direct-answer path: no retrieval, no RAG.
            retrieved_citations = []
            retrieval_meta = {"document_hits": 0}
            skill_result = get_registry().get("direct_answer").invoke(
                {"user_message": question, "history": history},
                model_override=model,
            )
            answer = skill_result["answer"]
            provider = skill_result["provider"]
            finish_reason = skill_result["finish_reason"]

        for source in retrieved_citations:
            if source not in citations:
                citations.append(source)

        metadata.setdefault("retrieval", {})
        metadata["retrieval"].update(retrieval_meta)
        error = None
        fallback_used = state.get("fallback_used", False)
    except Exception as run_error:
        answer = fallback_answer
        provider = None
        finish_reason = "error"
        error = str(run_error)
        fallback_used = True

    metadata = update_node_timing(metadata, node_name, (perf_counter() - started) * 1000)
    metadata["llm"] = {"provider": provider, "model": model, "finish_reason": finish_reason}

    return {
        "final_answer": answer,
        "citations": citations,
        "execution_metadata": metadata,
        "error": error,
        "fallback_used": fallback_used,
    }
