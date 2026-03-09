from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from research_agent.models import ResearchResult, ResearchTask
from research_agent.research_tool import ResearchTool
from research_agent.state import AgentState
from research_agent.utils.model_runtime import resolve_and_apply_model


async def execute_single_task(research_tool: ResearchTool, task: ResearchTask, timeout_seconds: float = 10.0) -> ResearchResult:
    """Execute one research task with timeout protection."""
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                research_tool.execute_task,
                task.order,
                task.query,
                task.goal,
            ),
            timeout=timeout_seconds,
        )
        return result
    except Exception as error:
        return ResearchResult(
            task_order=task.order,
            extracted_information="",
            sources=[],
            success=False,
            error=str(error),
        )


async def _execute_tasks_parallel(research_tool: ResearchTool, tasks: list[ResearchTask]) -> list[ResearchResult]:
    coroutines = [execute_single_task(research_tool, task) for task in tasks]
    results = await asyncio.gather(*coroutines, return_exceptions=False)
    return sorted(results, key=lambda item: item.task_order)


async def research_node(state: AgentState, research_tool: ResearchTool) -> dict[str, Any]:
    """Run research tasks concurrently and collect ordered results."""
    started = perf_counter()
    metadata = dict(state.get("execution_metadata") or {})
    resolve_and_apply_model(metadata, research_tool, fallback_model=getattr(research_tool, "model", None))
    plan = state.get("research_plan") or []
    if not plan:
        metadata.setdefault("node_timings", {})
        metadata["node_timings"]["research"] = (perf_counter() - started) * 1000
        return {"research_results": [], "execution_metadata": metadata}

    results = await _execute_tasks_parallel(research_tool, plan)
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
