from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse

from api.deps import get_research_agent_graph
from models.request import ChatRequest
from models.response import ChatResponse, ResponseError, ResponseMeta
from research_agent.graph import ResearchAgentGraph
from research_agent.streaming import SSEAdapter

try:
    from langsmith import traceable
except Exception:  # pragma: no cover - optional dependency at runtime
    traceable = None

router = APIRouter()
logger = logging.getLogger("api.chat_v2")


def _is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _langsmith_manual_tracing_enabled() -> bool:
    if traceable is None:
        return False
    if not os.getenv("LANGSMITH_API_KEY", "").strip():
        return False
    return _is_truthy_env("LANGSMITH_TRACING") or _is_truthy_env("LANGCHAIN_TRACING_V2")


def _map_execution_error(error: Exception) -> tuple[str, str]:
    message = str(error)
    lowered = message.lower()
    if "resource_exhausted" in lowered or "quota" in lowered or "429" in lowered:
        return "MODEL_ERROR", "Model đang quá tải hoặc hết quota tạm thời. Bạn thử lại sau ít phút nhé."
    if "timed out" in lowered or "timeout" in lowered:
        return "MODEL_ERROR", "Model phản hồi quá chậm. Bạn thử lại sau ít phút nhé."
    return "EXECUTION_ERROR", message or "LangGraph execution failed"


async def run_chat_v2_non_stream(
    payload: ChatRequest,
    request_id: str,
    graph: ResearchAgentGraph,
) -> ChatResponse:
    """Run LangGraph request and map final state to ChatResponse."""
    try:
        if _langsmith_manual_tracing_enabled():
            traced_invoke = traceable(name="api.v2.chat.non_stream", run_type="chain")(graph.ainvoke)
            final_state = await traced_invoke(payload, request_id=request_id)
        else:
            final_state = await graph.ainvoke(payload, request_id=request_id)
    except Exception as execution_error:
        code, mapped_message = _map_execution_error(execution_error)
        logger.exception("chat_v2_execution_error request_id=%s error=%s", request_id, execution_error)
        return ChatResponse(
            request_id=request_id,
            conversation_id=payload.conversation_id,
            status="error",
            answer="",
            sources=[],
            error=ResponseError(code=code, message=mapped_message),
            meta=ResponseMeta(
                provider=None,
                model=payload.model,
                finish_reason="error",
            ),
        )

    metadata = final_state.get("execution_metadata") or {}
    llm_metadata = metadata.get("llm") or {}
    response_model = str(llm_metadata.get("model") or metadata.get("model") or payload.model or "").strip() or None
    error = final_state.get("error")
    error_payload = None
    if error:
        error_code, error_message = _map_execution_error(Exception(str(error)))
        error_payload = ResponseError(code=error_code, message=error_message)

    return ChatResponse(
        request_id=str(metadata.get("request_id") or request_id),
        conversation_id=str(metadata.get("conversation_id") or payload.conversation_id or ""),
        status="error" if error_payload else "ok",
        answer=str(final_state.get("final_answer") or ""),
        sources=list(final_state.get("citations") or []),
        error=error_payload,
        meta=ResponseMeta(
            provider=str(llm_metadata.get("provider") or metadata.get("provider") or "langgraph"),
            model=response_model,
            finish_reason=str(llm_metadata.get("finish_reason") or "stop"),
        ),
    )


async def _stream_response(payload: ChatRequest, request_id: str, graph: ResearchAgentGraph):
    max_attempts = 2
    attempt = 1

    while attempt <= max_attempts:
        try:
            graph_stream = graph.astream(payload, request_id=request_id)
            async for sse_event in SSEAdapter.stream_to_sse(graph_stream):
                yield sse_event
            return
        except Exception as execution_error:
            code, mapped_message = _map_execution_error(execution_error)

            is_retryable = code == "MODEL_ERROR"
            if is_retryable and attempt < max_attempts:
                retry_event = {
                    "type": "status",
                    "node": "retry",
                    "message": "Model đang bận, hệ thống đang thử lại...",
                    "progress": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "attempt": attempt + 1,
                        "max_attempts": max_attempts,
                        "reason": code,
                    },
                    "model_runtime": {
                        "model": payload.model,
                        "provider": "langgraph",
                        "finish_reason": "retry",
                    },
                }
                logger.warning(
                    "chat_v2_stream_retry request_id=%s attempt=%s error=%s",
                    request_id,
                    attempt,
                    execution_error,
                )
                yield f"data: {json.dumps(retry_event, ensure_ascii=False)}\n\n"
                attempt += 1
                continue

            logger.exception(
                "chat_v2_stream_error request_id=%s attempt=%s error=%s",
                request_id,
                attempt,
                execution_error,
            )
            done_event = {
                "type": "done",
                "node": "done",
                "message": "Hoàn tất xử lý",
                "progress": 100,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model_runtime": {
                    "model": payload.model,
                    "provider": "langgraph",
                    "finish_reason": "error",
                },
                "data": {
                    "answer": "",
                    "citations": [],
                    "metadata": {
                        "request_id": request_id,
                        "conversation_id": payload.conversation_id,
                    },
                    "error": {
                        "code": code,
                        "message": mapped_message,
                    },
                },
            }
            yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return


@router.post("/api/v2/chat")
async def chat_v2(
    payload: ChatRequest,
    request: Request,
    response: Response,
    stream: bool = Query(default=False),
    graph: ResearchAgentGraph = Depends(get_research_agent_graph),
):
    """LangGraph-based chat endpoint supporting stream and non-stream modes."""
    request_id = request.headers.get("x-request-id") or str(uuid4())
    response.headers["x-api-version"] = "2"
    logger.info("incoming_chat_v2 request_id=%s stream=%s", request_id, stream)

    if stream:
        return StreamingResponse(
            _stream_response(payload, request_id=request_id, graph=graph),
            media_type="text/event-stream",
            headers={"x-api-version": "2"},
        )

    return await run_chat_v2_non_stream(payload, request_id=request_id, graph=graph)
