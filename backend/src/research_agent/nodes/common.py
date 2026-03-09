from __future__ import annotations

from time import perf_counter
from typing import Any

from research_agent.database import Database
from research_agent.direct_llm import DirectLLM
from research_agent.state import AgentState
from research_agent.utils.model_runtime import resolve_and_apply_model


def extract_last_message_content(state: AgentState) -> str:
    messages = state.get("messages") or []
    if not messages:
        return ""
    content = getattr(messages[-1], "content", "")
    return content if isinstance(content, str) else str(content)


def run_llm_node(
    state: AgentState,
    direct_llm: DirectLLM,
    database: Database,
    *,
    node_name: str,
    fallback_answer: str,
) -> dict[str, Any]:
    started = perf_counter()
    question = extract_last_message_content(state)

    metadata = dict(state.get("execution_metadata") or {})
    model = resolve_and_apply_model(metadata, direct_llm, fallback_model=getattr(direct_llm, "model", None))
    conversation_id = metadata.get("conversation_id")
    if not conversation_id:
        conversation_id = database.create_conversation()
        metadata["conversation_id"] = conversation_id

    try:
        history = database.get_conversation_history(conversation_id)
        answer, provider, finish_reason = direct_llm.generate_response(
            user_message=question,
            history=history,
            model=model,
        )
        error = None
        fallback_used = state.get("fallback_used", False)
    except Exception as run_error:
        answer = fallback_answer
        provider = None
        finish_reason = "error"
        error = str(run_error)
        fallback_used = True

    metadata.setdefault("node_timings", {})
    metadata["node_timings"][node_name] = (perf_counter() - started) * 1000
    metadata["llm"] = {"provider": provider, "model": model, "finish_reason": finish_reason}

    return {
        "final_answer": answer,
        "execution_metadata": metadata,
        "error": error,
        "fallback_used": fallback_used,
    }
