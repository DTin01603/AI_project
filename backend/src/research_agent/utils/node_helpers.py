"""Node helper utilities for timing, metadata, and common patterns.

Consolidates boilerplate used in every node.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable, TypeVar, cast

from research_agent.state import AgentState

T = TypeVar("T")


class NodeTimer:
    """Context manager for node execution timing."""

    def __init__(self, node_name: str) -> None:
        self.node_name = node_name
        self.start_time = perf_counter()
        self.elapsed_ms = 0.0

    def __enter__(self) -> "NodeTimer":
        self.start_time = perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed_ms = (perf_counter() - self.start_time) * 1000

    def to_dict(self) -> dict[str, float]:
        """Return timing as dict for metadata."""
        return {self.node_name: self.elapsed_ms}


def get_execution_metadata(state: AgentState) -> dict[str, Any]:
    """Extract execution metadata from state, creating if missing."""
    metadata = dict(state.get("execution_metadata") or {})
    metadata.setdefault("node_timings", {})
    return metadata


def update_node_timing(
    metadata: dict[str, Any],
    node_name: str,
    elapsed_ms: float,
) -> dict[str, Any]:
    """Add node timing to metadata."""
    metadata.setdefault("node_timings", {})
    metadata["node_timings"][node_name] = elapsed_ms
    return metadata


def node_timing_wrapper(node_name: str) -> Callable:
    """Decorator for automatic node timing.
    
    Usage:
        @node_timing_wrapper("complexity")
        def my_node(state: AgentState) -> dict[str, Any]:
            # timing is automatically recorded
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(state: AgentState, *args: Any, **kwargs: Any) -> dict[str, Any]:
            with NodeTimer(node_name) as timer:
                result = func(state, *args, **kwargs)
            
            if not isinstance(result, dict):
                result = {}
            
            metadata = get_execution_metadata(state)
            metadata = update_node_timing(metadata, node_name, timer.elapsed_ms)
            result["execution_metadata"] = metadata
            return result
        return wrapper
    return decorator


def get_last_message_text(state: AgentState) -> str:
    """Extract text content from last message in state."""
    messages = state.get("messages") or []
    if not messages:
        return ""
    
    last_msg = messages[-1]
    content = getattr(last_msg, "content", "")
    return content if isinstance(content, str) else str(content)


def merge_state_update(
    base_update: dict[str, Any],
    metadata_update: dict[str, Any],
) -> dict[str, Any]:
    """Merge a state update with metadata update.
    
    Ensures execution_metadata is properly merged without overwriting.
    """
    if "execution_metadata" in metadata_update:
        base_metadata = base_update.get("execution_metadata") or {}
        new_metadata = metadata_update["execution_metadata"]
        
        # Merge metadata dicts
        merged_metadata = {**base_metadata, **new_metadata}
        
        # Merge nested node_timings
        if "node_timings" in base_metadata and "node_timings" in new_metadata:
            merged_metadata["node_timings"] = {
                **base_metadata.get("node_timings", {}),
                **new_metadata.get("node_timings", {}),
            }
        
        return {**base_update, **metadata_update, "execution_metadata": merged_metadata}
    
    return {**base_update, **metadata_update}


def extract_error_context(state: AgentState) -> dict[str, Any]:
    """Extract relevant context when error occurs."""
    return {
        "last_message": get_last_message_text(state),
        "conversation_id": state.get("execution_metadata", {}).get("conversation_id"),
        "query_type": state.get("query_type"),
        "previous_error": state.get("error"),
    }


__all__ = [
    "NodeTimer",
    "get_execution_metadata",
    "update_node_timing",
    "node_timing_wrapper",
    "get_last_message_text",
    "merge_state_update",
    "extract_error_context",
]
