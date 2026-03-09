from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator


class SSEAdapter:
    """Convert LangGraph streaming updates to SSE-formatted payload strings."""

    NODE_EVENT_MAP: dict[str, dict[str, str]] = {
        "entry": {"type": "status", "message": "Đang xử lý câu hỏi..."},
        "complexity": {"type": "status", "message": "Đang phân tích độ phức tạp..."},
        "router": {"type": "status", "message": "Đang xác định luồng xử lý..."},
        "planning": {"type": "status", "message": "Đang lập kế hoạch nghiên cứu..."},
        "research": {"type": "status", "message": "Đang thực hiện nghiên cứu..."},
        "synthesis": {"type": "status", "message": "Đang tổng hợp kết quả..."},
        "citation": {"type": "status", "message": "Đang chuẩn hóa trích dẫn..."},
        "persist": {"type": "status", "message": "Đang lưu hội thoại..."},
        "simple_llm": {"type": "status", "message": "Đang tạo phản hồi..."},
        "direct_llm": {"type": "status", "message": "Đang tạo phản hồi..."},
        "current_date": {"type": "status", "message": "Đang lấy thông tin ngày hiện tại..."},
    }

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _total_nodes_for_query_type(query_type: str | None) -> int:
        if query_type == "simple":
            return 4
        if query_type == "research_intent":
            return 8
        if query_type == "current_date":
            return 5
        return 5

    @staticmethod
    def _extract_model_runtime(payload: dict[str, Any]) -> dict[str, Any]:
        metadata = payload.get("execution_metadata") or {}
        llm_metadata = metadata.get("llm") or {}

        model = str(llm_metadata.get("model") or metadata.get("model") or "").strip() or None
        provider = str(llm_metadata.get("provider") or metadata.get("provider") or "").strip() or None
        finish_reason = str(llm_metadata.get("finish_reason") or "").strip() or None

        return {
            "model": model,
            "provider": provider,
            "finish_reason": finish_reason,
        }

    @staticmethod
    async def stream_to_sse(graph_stream: AsyncIterator[dict[str, Any]]) -> AsyncIterator[str]:
        """Yield SSE lines from LangGraph update stream."""
        completed_nodes = 0
        final_payload: dict[str, Any] = {}

        async for update in graph_stream:
            if not update:
                continue

            node_name = next(iter(update.keys()))
            node_payload = update.get(node_name, {}) or {}
            if isinstance(node_payload, dict):
                final_payload.update(node_payload)

            completed_nodes += 1
            query_type = final_payload.get("query_type")
            total_nodes = SSEAdapter._total_nodes_for_query_type(query_type)
            progress = min(99, int((completed_nodes / max(total_nodes, 1)) * 100))

            event_meta = SSEAdapter.NODE_EVENT_MAP.get(
                node_name,
                {"type": "status", "message": f"Đang xử lý bước {node_name}..."},
            )
            event: dict[str, Any] = {
                "type": event_meta["type"],
                "node": node_name,
                "message": event_meta["message"],
                "progress": progress,
                "timestamp": SSEAdapter._now_iso(),
                "data": {},
                "model_runtime": SSEAdapter._extract_model_runtime(final_payload),
            }

            if node_name == "complexity":
                event["data"] = {"complexity": final_payload.get("complexity_result")}
            elif node_name == "planning":
                plan = final_payload.get("research_plan") or []
                event["data"] = {"tasks": [getattr(task, "query", "") for task in plan], "num_tasks": len(plan)}
            elif node_name == "research":
                results = final_payload.get("research_results") or []
                event["data"] = {
                    "num_results": len(results),
                    "successful": len([item for item in results if getattr(item, "success", False)]),
                }

            yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"

        done_event = {
            "type": "done",
            "node": "done",
            "message": "Hoàn tất xử lý",
            "progress": 100,
            "timestamp": SSEAdapter._now_iso(),
            "model_runtime": SSEAdapter._extract_model_runtime(final_payload),
            "data": {
                "answer": final_payload.get("final_answer", ""),
                "citations": final_payload.get("citations", []),
                "metadata": final_payload.get("execution_metadata", {}),
                "error": final_payload.get("error"),
            },
        }
        yield f"data: {json.dumps(done_event, ensure_ascii=False, default=str)}\n\n"
        yield "data: [DONE]\n\n"
