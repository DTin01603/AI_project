from __future__ import annotations

from time import perf_counter
from typing import Any

from research_agent.database import Database
from research_agent.nodes.common import extract_last_message_content
from research_agent.state import AgentState


def persist_conversation_node(state: AgentState, database: Database) -> dict[str, Any]:
    """Persist current user/assistant turn for every execution branch."""
    started = perf_counter()

    metadata = dict(state.get("execution_metadata") or {})
    conversation_id = str(metadata.get("conversation_id") or "").strip()
    if not conversation_id:
        conversation_id = database.create_conversation()
        metadata["conversation_id"] = conversation_id

    user_message = extract_last_message_content(state).strip()
    assistant_answer = str(state.get("final_answer") or "").strip()

    persistence_saved = False
    persistence_error: str | None = None
    try:
        if user_message:
            database.save_message(conversation_id, "user", user_message)
        if assistant_answer:
            database.save_message(conversation_id, "assistant", assistant_answer)
        persistence_saved = True
    except Exception as error:
        persistence_error = str(error)

    metadata.setdefault("node_timings", {})
    metadata["node_timings"]["persist"] = (perf_counter() - started) * 1000
    metadata["persistence"] = {
        "saved": persistence_saved,
        "error": persistence_error,
    }

    return {
        "execution_metadata": metadata,
    }
