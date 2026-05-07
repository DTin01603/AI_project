from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from agent.models import ResearchResult, ResearchTask
from agent.state import AgentState
from agent.utils.model_runtime import resolve_and_apply_model
from skills import get_registry
from skills.research_search.handler import to_research_result


async def execute_single_task(
    task: ResearchTask,
    timeout_seconds: float = 10.0,
    model_override: str | None = None,
) -> ResearchResult:
    """Execute one research task with timeout protection via the research_search skill."""

    def _run_via_skill() -> ResearchResult:
        skill = get_registry().get("research_search")
        out = skill.invoke(
            {"task_order": task.order, "query": task.query, "goal": task.goal},
            model_override=model_override,
        )
        return to_research_result(out)

    try:
        result = await asyncio.wait_for(asyncio.to_thread(_run_via_skill), timeout=timeout_seconds)
        return result
    except Exception as error:
        return ResearchResult(
            task_order=task.order,
            extracted_information="",
            sources=[],
            success=False,
            error=str(error),
        )


async def _execute_tasks_parallel(
    tasks: list[ResearchTask],
    model_override: str | None,
) -> list[ResearchResult]:
    coroutines = [execute_single_task(task, model_override=model_override) for task in tasks]
    results = await asyncio.gather(*coroutines, return_exceptions=False)
    return sorted(results, key=lambda item: item.task_order)


async def research_node(state: AgentState) -> dict[str, Any]:
    """Run research tasks concurrently and collect ordered results."""
    started = perf_counter()
    metadata = dict(state.get("execution_metadata") or {})
    model_override = metadata.get("model") or None
    resolve_and_apply_model(metadata)
    plan = state.get("research_plan") or []
    if not plan:
        metadata.setdefault("node_timings", {})
        metadata["node_timings"]["research"] = (perf_counter() - started) * 1000
        return {"research_results": [], "execution_metadata": metadata}

    results = await _execute_tasks_parallel(plan, model_override)
    success_count = len([result for result in results if result.success])

    metadata.setdefault("node_timings", {})
    metadata.setdefault("research", {})
    metadata["node_timings"]["research"] = (perf_counter() - started) * 1000
    metadata["research"] = {
        "num_tasks": len(plan),
        "successful_tasks": success_count,
    }

    return {
        "research_results": results,
        "execution_metadata": metadata,
    }
