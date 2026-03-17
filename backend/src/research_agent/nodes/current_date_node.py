from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from research_agent.state import AgentState
from research_agent.utils import get_execution_metadata, node_timing_wrapper


@node_timing_wrapper("current_date")
def current_date_node(state: AgentState) -> dict[str, Any]:
    """Return current date in Vietnam timezone and persist to conversation."""
    answer = f"Hôm nay là ngày {datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y')} (theo giờ Việt Nam)."

    metadata = get_execution_metadata(state)

    return {
        "final_answer": answer,
        "execution_metadata": metadata,
    }
