from __future__ import annotations

from typing import Any

from research_agent.complexity_analyzer import ComplexityAnalyzer
from research_agent.nodes.common import extract_last_message_content
from research_agent.state import AgentState
from research_agent.utils import get_execution_metadata, node_timing_wrapper, update_node_timing
from research_agent.utils.intent_patterns import (
    is_current_date_request,
    is_research_intent_request,
    is_time_sensitive_request,
)
from research_agent.utils.model_runtime import resolve_and_apply_model


@node_timing_wrapper("complexity")
def complexity_node(state: AgentState, analyzer: ComplexityAnalyzer | None = None) -> dict[str, Any]:
    """Classify query complexity and update routing state."""
    message = extract_last_message_content(state)
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

    metadata = get_execution_metadata(state)
    resolve_and_apply_model(metadata, runtime_analyzer, fallback_model=getattr(runtime_analyzer, "model", None))

    try:
        result = runtime_analyzer.analyze(message)
    except Exception:
        result = ComplexityAnalyzer._heuristic(message)
        fallback_used = True

    force_complex = (
        is_current_date_request(message)
        or is_time_sensitive_request(message)
        or is_research_intent_request(message)
    )
    if force_complex and not result.is_complex:
        result.is_complex = True
        result.reason = "intent_override"

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
