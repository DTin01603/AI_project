from __future__ import annotations

from time import perf_counter
from typing import Any

from research_agent.complexity_analyzer import ComplexityAnalyzer
from research_agent.nodes.router_node import (
    _is_current_date_request,
    _is_research_intent_request,
    _is_time_sensitive_request,
)
from research_agent.state import AgentState
from research_agent.utils.model_runtime import resolve_and_apply_model


def _extract_last_message_content(state: AgentState) -> str:
    messages = state.get("messages") or []
    if not messages:
        return ""
    last_message = messages[-1]
    content = getattr(last_message, "content", "")
    if isinstance(content, str):
        return content
    return str(content)


def complexity_node(state: AgentState, analyzer: ComplexityAnalyzer | None = None) -> dict[str, Any]:
    """Classify query complexity and update routing state."""
    started = perf_counter()
    message = _extract_last_message_content(state)
    if not message.strip():
        return {
            "query_type": "simple",
            "complexity_result": {
                "is_complex": False,
                "confidence": 1.0,
                "reason": "empty_message_default",
            },
            "fallback_used": True,
            "error": "empty_message",
        }

    runtime_analyzer = analyzer or ComplexityAnalyzer()
    fallback_used = False

    metadata = dict(state.get("execution_metadata") or {})
    resolve_and_apply_model(metadata, runtime_analyzer, fallback_model=getattr(runtime_analyzer, "model", None))

    try:
        result = runtime_analyzer.analyze(message)
    except Exception:
        result = ComplexityAnalyzer._heuristic(message)
        fallback_used = True

    force_complex = (
        _is_current_date_request(message)
        or _is_time_sensitive_request(message)
        or _is_research_intent_request(message)
    )
    if force_complex and not result.is_complex:
        result.is_complex = True
        result.reason = "intent_override"

    metadata.setdefault("node_timings", {})
    metadata["node_timings"]["complexity"] = (perf_counter() - started) * 1000

    return {
        "query_type": "complex" if result.is_complex else "simple",
        "complexity_result": {
            "is_complex": result.is_complex,
            "confidence": result.confidence,
            "reason": result.reason,
        },
        "execution_metadata": metadata,
        "fallback_used": state.get("fallback_used", False) or fallback_used,
    }
