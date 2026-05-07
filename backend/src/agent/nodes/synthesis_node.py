from __future__ import annotations

from typing import Any

from services.research_aggregation_service import ResearchAggregationService
from agent.nodes.common import extract_last_message_content
from agent.state import AgentState
from agent.utils import get_execution_metadata, node_timing_wrapper
from agent.utils.model_runtime import resolve_and_apply_model
from skills import get_registry


@node_timing_wrapper("synthesis")
def synthesis_node(
    state: AgentState,
    aggregator: ResearchAggregationService,
) -> dict[str, Any]:
    """Synthesize research results into final answer via skills."""
    question = extract_last_message_content(state)
    metadata = get_execution_metadata(state)
    model = resolve_and_apply_model(metadata)
    results = state.get("research_results") or []
    successful = [result for result in results if result.success]

    fallback_used = False
    registry = get_registry()
    if not successful:
        try:
            skill_result = registry.get("direct_answer").invoke(
                {"user_message": question, "history": []},
                model_override=model,
            )
            answer = skill_result["answer"]
            provider = skill_result["provider"]
            finish_reason = skill_result["finish_reason"]
            error = None
        except Exception as run_error:
            answer = "Xin lỗi, hệ thống chưa thể trả lời ngay lúc này. Bạn thử lại sau ít phút nhé."
            provider = None
            finish_reason = "error"
            error = str(run_error)
        citations: list[str] = []
        fallback_used = True
    else:
        knowledge_base, citations = aggregator.aggregate(successful)
        try:
            skill_result = registry.get("response_composer").invoke(
                {"question": question, "knowledge_base": knowledge_base},
                model_override=model,
            )
            answer = skill_result["answer"]
        except Exception:
            answer = knowledge_base or "Xin lỗi, hệ thống chưa tổng hợp được câu trả lời."
            fallback_used = True
        provider = None
        finish_reason = "stop"
        error = None

    metadata["llm"] = {
        "provider": provider,
        "model": model,
        "finish_reason": finish_reason,
    }

    return {
        "final_answer": answer,
        "citations": citations,
        "execution_metadata": metadata,
        "error": error,
        "fallback_used": state.get("fallback_used", False) or fallback_used,
    }
