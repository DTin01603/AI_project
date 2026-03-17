from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from research_agent.state import AgentState
from research_agent.utils import get_execution_metadata, node_timing_wrapper


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@node_timing_wrapper("entry")
def entry_node(state: AgentState) -> dict[str, Any]:
    """Initialize execution metadata and validate input messages."""
    messages = state.get("messages") or []
    if not messages:
        return {
            "error": "empty_messages",
            "fallback_used": True,
        }

    metadata = get_execution_metadata(state)
    metadata.setdefault("started_at", _now_iso())
    metadata.setdefault("conversation_id", str(uuid4()))
    metadata.setdefault("request_id", str(uuid4()))

    return {"execution_metadata": metadata}
