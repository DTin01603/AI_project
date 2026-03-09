from __future__ import annotations

from time import perf_counter
from typing import Any

from research_agent.models import ResearchTask
from research_agent.nodes.common import extract_last_message_content
from research_agent.planning_agent import PlanningAgent
from research_agent.state import AgentState
from research_agent.utils.model_runtime import resolve_and_apply_model


def planning_node(state: AgentState, planning_agent: PlanningAgent | None = None) -> dict[str, Any]:
    """Create research plan and record planning metrics."""
    started = perf_counter()
    message = extract_last_message_content(state)

    runtime_agent = planning_agent or PlanningAgent()
    fallback_used = False
    metadata = dict(state.get("execution_metadata") or {})
    resolve_and_apply_model(metadata, runtime_agent, fallback_model=getattr(runtime_agent, "model", None))
    try:
        tasks = runtime_agent.create_plan(message)
    except Exception:
        tasks = [ResearchTask(order=1, query=message, goal="Thu thập thông tin chính")]
        fallback_used = True

    if not tasks:
        tasks = [ResearchTask(order=1, query=message, goal="Thu thập thông tin chính")]
        fallback_used = True

    metadata.setdefault("node_timings", {})
    metadata.setdefault("planning", {})
    metadata["node_timings"]["planning"] = (perf_counter() - started) * 1000
    metadata["planning"] = {
        "num_tasks": len(tasks),
        "queries": [task.query for task in tasks],
    }

    return {
        "research_plan": tasks,
        "execution_metadata": metadata,
        "fallback_used": state.get("fallback_used", False) or fallback_used,
    }
