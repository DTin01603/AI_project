from __future__ import annotations

from typing import Any

from research_agent.state import AgentState
from research_agent.utils import deduplicate_list, get_execution_metadata, node_timing_wrapper


@node_timing_wrapper("citation")
def citation_node(state: AgentState) -> dict[str, Any]:
    """Append deduplicated citation list to final answer."""
    answer = (state.get("final_answer") or "").strip()
    raw_citations = [item.strip() for item in (state.get("citations") or []) if item and item.strip()]
    citations = deduplicate_list(raw_citations, key_func=lambda item: item.lower())

    if citations:
        citation_block = "\n".join(f"- {item}" for item in citations)
        answer = f"{answer}\n\nNguồn tham khảo:\n{citation_block}".strip()

    metadata = get_execution_metadata(state)

    return {
        "final_answer": answer,
        "citations": citations,
        "execution_metadata": metadata,
    }
