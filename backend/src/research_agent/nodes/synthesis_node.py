from __future__ import annotations

from time import perf_counter
from typing import Any

from research_agent.aggregator import Aggregator
from research_agent.direct_llm import DirectLLM
from research_agent.nodes.common import extract_last_message_content
from research_agent.response_composer import ResponseComposer
from research_agent.state import AgentState
from research_agent.utils.model_runtime import resolve_and_apply_model


def synthesis_node(
    state: AgentState,
    aggregator: Aggregator,
    response_composer: ResponseComposer,
    direct_llm: DirectLLM,
) -> dict[str, Any]:
    """Synthesize research results into final answer with fallback path."""
    started = perf_counter()
    question = extract_last_message_content(state)
    metadata = dict(state.get("execution_metadata") or {})
    model = resolve_and_apply_model(
        metadata,
        response_composer,
        direct_llm,
        fallback_model=getattr(direct_llm, "model", None),
    )
    results = state.get("research_results") or []
    successful = [result for result in results if result.success]

    fallback_used = False
    if not successful:
        try:
            answer, provider, finish_reason = direct_llm.generate_response(
                user_message=question,
                history=[],
                model=model,
            )
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
        answer = response_composer.compose(question, knowledge_base)
        provider = None
        finish_reason = "stop"
        error = None

    metadata.setdefault("node_timings", {})
    metadata["node_timings"]["synthesis"] = (perf_counter() - started) * 1000
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
