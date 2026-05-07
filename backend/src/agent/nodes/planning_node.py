from __future__ import annotations

from typing import Any

from agent.models import ResearchTask
from agent.nodes.common import extract_last_message_content
from agent.state import AgentState
from agent.utils import get_execution_metadata, node_timing_wrapper
from skills import get_registry
from skills.planning.handler import to_research_tasks


@node_timing_wrapper("planning")
def planning_node(state: AgentState) -> dict[str, Any]:
    """Create research plan via planning skill."""
    message = extract_last_message_content(state)
    fallback_used = False
    metadata = get_execution_metadata(state)
    model_override = metadata.get("model") or None

    try:
        result = get_registry().get("planning").invoke({"question": message}, model_override=model_override)
        tasks = to_research_tasks(result)
    except Exception:
        tasks = [ResearchTask(order=1, query=message, goal="Thu thập thông tin chính")]
        fallback_used = True

    if not tasks:
        tasks = [ResearchTask(order=1, query=message, goal="Thu thập thông tin chính")]
        fallback_used = True

    metadata.setdefault("planning", {})
    metadata["planning"] = {
        "num_tasks": len(tasks),
        "queries": [task.query for task in tasks],
    }

    return {
        "research_plan": tasks,
        "execution_metadata": metadata,
        "fallback_used": state.get("fallback_used", False) or fallback_used,
    }
