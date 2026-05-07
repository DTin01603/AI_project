"""Node timing + execution-metadata helpers used by every node."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from agent.state import AgentState


class _NodeTimer:
    """Internal context manager for node execution timing."""

    def __init__(self, node_name: str) -> None:
        self.node_name = node_name
        self.start_time = perf_counter()
        self.elapsed_ms = 0.0

    def __enter__(self) -> "_NodeTimer":
        self.start_time = perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed_ms = (perf_counter() - self.start_time) * 1000


def get_execution_metadata(state: AgentState) -> dict[str, Any]:
    """Return a mutable copy of ``state['execution_metadata']`` with ``node_timings`` initialised."""
    metadata = dict(state.get("execution_metadata") or {})
    metadata.setdefault("node_timings", {})
    return metadata


def update_node_timing(
    metadata: dict[str, Any],
    node_name: str,
    elapsed_ms: float,
) -> dict[str, Any]:
    """Record ``elapsed_ms`` for ``node_name`` inside ``metadata['node_timings']``."""
    metadata.setdefault("node_timings", {})
    metadata["node_timings"][node_name] = elapsed_ms
    return metadata


def node_timing_wrapper(node_name: str) -> Callable:
    """Decorator that times a node function and merges the timing into execution_metadata."""

    def decorator(func: Callable) -> Callable:
        def wrapper(state: AgentState, *args: Any, **kwargs: Any) -> dict[str, Any]:
            with _NodeTimer(node_name) as timer:
                result = func(state, *args, **kwargs)
            if not isinstance(result, dict):
                result = {}
            metadata = get_execution_metadata(state)
            metadata = update_node_timing(metadata, node_name, timer.elapsed_ms)
            result["execution_metadata"] = metadata
            return result
        return wrapper

    return decorator


__all__ = [
    "get_execution_metadata",
    "update_node_timing",
    "node_timing_wrapper",
]
