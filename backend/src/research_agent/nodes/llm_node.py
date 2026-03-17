"""Unified LLM node for generating responses (with or without agentic RAG).

This module consolidates the logic from simple_llm_node and direct_llm_node
to reduce duplication. Both simple and direct paths now use the same
underlying implementation with different fallback messages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from research_agent.database import Database
from research_agent.direct_llm import DirectLLM
from research_agent.nodes.common import run_llm_node
from rag.retrieval_node import RetrievalNode
from research_agent.state import AgentState

if TYPE_CHECKING:
    from rag.subgraph import RAGSubgraph


def llm_node(
    state: AgentState,
    direct_llm: DirectLLM,
    database: Database,
    *,
    node_name: str = "llm",
    fallback_answer: str = "Xin lỗi, chưa thể tạo phản hồi lúc này.",
    retrieval_node: RetrievalNode | None = None,
    rag_subgraph: "RAGSubgraph | None" = None,
) -> dict[str, Any]:
    """Generate response with optional agentic RAG subgraph.

    Args:
        state: Agent state dict
        direct_llm: LLM generator
        database: Conversation storage
        node_name: Name for logging (e.g., 'simple_llm', 'direct_llm')
        fallback_answer: Message when generation fails
        retrieval_node: Optional legacy retrieval node (ignored if rag_subgraph present)
        rag_subgraph: Optional agentic RAG subgraph for self-correcting retrieval

    Returns:
        State update dict with final_answer, citations, etc.
    """
    return run_llm_node(
        state,
        direct_llm,
        database,
        retrieval_node=retrieval_node,
        node_name=node_name,
        fallback_answer=fallback_answer,
        rag_subgraph=rag_subgraph,
    )


__all__ = ["llm_node"]
