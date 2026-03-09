from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any
from zoneinfo import ZoneInfo

from research_agent.state import AgentState


def current_date_node(state: AgentState) -> dict[str, Any]:
    """Return current date in Vietnam timezone and persist to conversation."""
    started = perf_counter()
    answer = f"Hôm nay là ngày {datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y')} (theo giờ Việt Nam)."

    metadata = dict(state.get("execution_metadata") or {})
    metadata.setdefault("node_timings", {})
    metadata["node_timings"]["current_date"] = (perf_counter() - started) * 1000

    return {
        "final_answer": answer,
        "execution_metadata": metadata,
    }
