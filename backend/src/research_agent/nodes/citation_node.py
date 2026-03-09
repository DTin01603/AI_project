from __future__ import annotations

from time import perf_counter
from typing import Any

from research_agent.state import AgentState


def _deduplicate_sources(sources: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for source in sources:
        normalized = source.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        output.append(normalized)
    return output


def citation_node(state: AgentState) -> dict[str, Any]:
    """Append deduplicated citation list to final answer."""
    started = perf_counter()
    answer = (state.get("final_answer") or "").strip()
    citations = _deduplicate_sources(state.get("citations") or [])

    if citations:
        citation_block = "\n".join(f"- {item}" for item in citations)
        answer = f"{answer}\n\nNguồn tham khảo:\n{citation_block}".strip()

    metadata = dict(state.get("execution_metadata") or {})
    metadata.setdefault("node_timings", {})
    metadata["node_timings"]["citation"] = (perf_counter() - started) * 1000

    return {
        "final_answer": answer,
        "citations": citations,
        "execution_metadata": metadata,
    }
