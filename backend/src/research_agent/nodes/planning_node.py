from __future__ import annotations

from typing import Any

from research_agent.models import ResearchTask
from research_agent.nodes.common import extract_last_message_content
from research_agent.planning_agent import PlanningAgent
from research_agent.state import AgentState
from research_agent.utils import get_execution_metadata, node_timing_wrapper
from research_agent.utils.model_runtime import resolve_and_apply_model


@node_timing_wrapper("planning")
def planning_node(state: AgentState, planning_agent: PlanningAgent | None = None) -> dict[str, Any]:
    """Create research plan and record planning metrics."""
    message = extract_last_message_content(state)

    runtime_agent = planning_agent or PlanningAgent()
    fallback_used = False
    metadata = get_execution_metadata(state)
    resolve_and_apply_model(metadata, runtime_agent, fallback_model=getattr(runtime_agent, "model", None))
    try:
        tasks = runtime_agent.create_plan(message)
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
