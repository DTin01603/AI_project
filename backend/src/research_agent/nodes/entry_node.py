from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from research_agent.state import AgentState


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def entry_node(state: AgentState) -> dict[str, Any]:
    """Initialize execution metadata and validate input messages."""
    started = perf_counter()

    messages = state.get("messages") or []
    if not messages:
        return {
            "error": "empty_messages",
            "fallback_used": True,
            "execution_metadata": {
                "node_timings": {"entry": (perf_counter() - started) * 1000},
                "started_at": _now_iso(),
            },
        }

    metadata = dict(state.get("execution_metadata") or {})
    metadata.setdefault("started_at", _now_iso())
    metadata.setdefault("conversation_id", str(uuid4()))
    metadata.setdefault("request_id", str(uuid4()))
    metadata.setdefault("node_timings", {})
    metadata["node_timings"]["entry"] = (perf_counter() - started) * 1000

    return {"execution_metadata": metadata}
