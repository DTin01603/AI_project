"""Unified LLM node for generating responses (with or without agentic RAG)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent.nodes.retrieval_node import RetrievalNode
from agent.nodes.common import run_llm_node
from agent.state import AgentState
from services.conversation_service import ConversationService

if TYPE_CHECKING:
    from agent.subgraph import RAGSubgraph


def llm_node(
    state: AgentState,
    conversation_service: ConversationService,
    *,
    node_name: str = "llm",
    fallback_answer: str = "Xin lỗi, chưa thể tạo phản hồi lúc này.",
    retrieval_node: RetrievalNode | None = None,
    rag_subgraph: "RAGSubgraph | None" = None,
) -> dict[str, Any]:
    """Generate response with optional agentic RAG subgraph.

    Args:
        state: Agent state dict
        conversation_service: Conversation persistence + history retrieval
        node_name: Name for logging (e.g., 'direct_answer', 'local_rag')
        fallback_answer: Message when generation fails
        retrieval_node: Optional legacy retrieval node (ignored if rag_subgraph present)
        rag_subgraph: Optional agentic RAG subgraph for self-correcting retrieval

    Returns:
        State update dict with final_answer, citations, etc.
    """
    return run_llm_node(
        state,
        conversation_service,
        retrieval_node=retrieval_node,
        node_name=node_name,
        fallback_answer=fallback_answer,
        rag_subgraph=rag_subgraph,
    )


__all__ = ["llm_node"]
