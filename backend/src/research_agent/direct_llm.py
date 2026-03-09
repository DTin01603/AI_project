from __future__ import annotations

from adapters import get_adapter_for_model
from adapters.base import BaseAdapter
from research_agent.resilience import call_with_retry, with_timeout


class DirectLLM:
    SYSTEM_PROMPT = (
        "Bạn là trợ lý AI hữu ích. Trả lời rõ ràng, ngắn gọn, đúng ngôn ngữ người dùng. "
        "Với dữ liệu thời gian thực (giá, tỷ giá, chỉ số, thời tiết hiện tại), "
        "không tự suy đoán số liệu nếu chưa có nguồn cập nhật."
    )

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        max_history_messages: int = 12,
        max_history_chars: int = 6000,
        max_turn_chars: int = 1200,
        adapter: BaseAdapter | None = None,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_history_messages = max_history_messages
        self.max_history_chars = max_history_chars
        self.max_turn_chars = max_turn_chars
        self.adapter = adapter or get_adapter_for_model(model)

    def _trim_content(self, text: str) -> str:
        normalized = (text or "").strip()
        if len(normalized) <= self.max_turn_chars:
            return normalized
        return normalized[-self.max_turn_chars :]

    def _select_history(self, history: list[dict[str, str]]) -> list[tuple[str, str]]:
        selected: list[tuple[str, str]] = []
        total_chars = 0

        for item in reversed(history):
            role = item.get("role")
            content = self._trim_content(item.get("content", ""))
            if role not in {"user", "assistant"} or not content:
                continue

            if len(selected) >= self.max_history_messages:
                break
            if total_chars + len(content) > self.max_history_chars:
                break

            selected.append((role, content))
            total_chars += len(content)

        selected.reverse()
        return selected

    def _build_messages(self, user_message: str, history: list[dict[str, str]]) -> list[tuple[str, str]]:
        # Build chat context from system prompt + prior turns + current user message.
        messages: list[tuple[str, str]] = [("system", self.SYSTEM_PROMPT)]
        messages.extend(self._select_history(history))
        messages.append(("user", self._trim_content(user_message)))
        return messages

    def generate_response(
        self,
        user_message: str,
        history: list[dict[str, str]],
        model: str | None = None,
    ) -> tuple[str, str, str]:
        # Invoke LLM with timeout/retry and return answer with provider metadata.
        selected_model = (model or self.model).strip() or self.model
        adapter = self.adapter if selected_model == self.model else get_adapter_for_model(selected_model)
        messages = self._build_messages(user_message, history)

        def _invoke_once() -> tuple[str, str, str]:
            def _run():
                output = adapter.invoke(
                    model=selected_model,
                    messages=messages,
                    constraints={"temperature": 0.3, "max_output_tokens": 1200},
                )
                return output

            output = with_timeout(_run, self.timeout_seconds, "direct_llm")
            answer = (output.answer_text or "").strip()
            if not answer:
                raise ValueError("model returned empty output")
            return answer, adapter.provider, output.finish_reason

        def _is_retryable(error: Exception) -> bool:
            lowered = str(error).lower()
            non_retryable_markers = ["empty output", "bad request", "invalid"]
            return not any(marker in lowered for marker in non_retryable_markers)

        return call_with_retry(
            operation=_invoke_once,
            max_retries=self.max_retries,
            base_delay_seconds=1.0,
            is_retryable=_is_retryable,
        )
