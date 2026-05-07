from __future__ import annotations

from typing import Any

from agent.nodes.common import extract_last_message_content
from agent.state import AgentState
from agent.utils import get_execution_metadata, node_timing_wrapper
from services.conversation_service import ConversationService


@node_timing_wrapper("persist")
def persist_conversation_node(
    state: AgentState, conversation_service: ConversationService
) -> dict[str, Any]:
    """Persist current user/assistant turn for every execution branch.

    Both messages are written under one transaction so an error on the
    assistant insert rolls back the user insert too — no orphan rows.
    """
    metadata = get_execution_metadata(state)
    conversation_id = str(metadata.get("conversation_id") or "").strip()
    if not conversation_id:
        conversation_id = conversation_service.get_or_create_conversation(None)
        metadata["conversation_id"] = conversation_id

    user_message = extract_last_message_content(state).strip()
    assistant_answer = str(state.get("final_answer") or "").strip()

    persistence_saved = False
    persistence_error: str | None = None
    try:
        conversation_service.persist_turn(
            conversation_id, user_message, assistant_answer
        )
        persistence_saved = True
    except Exception as error:
        persistence_error = str(error)

    metadata["persistence"] = {
        "saved": persistence_saved,
        "error": persistence_error,
    }

    return {
        "execution_metadata": metadata,
    }
