from __future__ import annotations

from typing import Any

from research_agent.database import Database
from research_agent.direct_llm import DirectLLM
from research_agent.nodes.common import run_llm_node
from rag.retrieval_node import RetrievalNode
from research_agent.state import AgentState


def direct_llm_node(
    state: AgentState,
    direct_llm: DirectLLM,
    database: Database,
    retrieval_node: RetrievalNode,
) -> dict[str, Any]:
    """Generate response for direct LLM branch or fallback from research."""
    return run_llm_node(
        state,
        direct_llm,
        database,
        retrieval_node=retrieval_node,
        node_name="direct_llm",
        fallback_answer="Xin lỗi, hệ thống chưa xử lý được yêu cầu này ngay bây giờ.",
    )
