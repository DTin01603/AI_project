from __future__ import annotations

from typing import Any

from research_agent.nodes.common import extract_last_message_content
from research_agent.state import AgentState
from research_agent.utils import get_execution_metadata, node_timing_wrapper, update_node_timing
from research_agent.utils.intent_patterns import (
    is_current_date_request,
    is_research_intent_request,
    is_time_sensitive_request,
)


@node_timing_wrapper("router")
def router_node(state: AgentState) -> dict[str, Any]:
    """Route complex queries into research/date/direct_llm branches."""
    message = extract_last_message_content(state)

    if is_current_date_request(message):
        route = "current_date"
        reason = "current_date_detected"
    elif is_time_sensitive_request(message) or is_research_intent_request(message):
        route = "research_intent"
        reason = "research_or_time_sensitive"
    else:
        route = "direct_llm"
        reason = "default_direct_llm"

    metadata = get_execution_metadata(state)
    metadata.setdefault("routing", {})
    metadata["routing"]["router"] = {"route": route, "reason": reason}

    return {
        "query_type": route,
        "execution_metadata": metadata,
    }
