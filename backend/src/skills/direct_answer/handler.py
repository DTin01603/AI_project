from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from agent.utils.resilience import call_with_retry, with_timeout
from skills._base import BaseSkill
from skills._errors import SkillValidationError
from skills._prompt_loader import render


class Inputs(BaseModel):
    user_message: str
    history: list[dict[str, str]] = []


class Outputs(BaseModel):
    answer: str
    provider: str | None = None
    finish_reason: str = "stop"


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def _cfg_int(self, key: str, default: int) -> int:
        return int(self.config.get(key, default))

    def _cfg_float(self, key: str, default: float) -> float:
        return float(self.config.get(key, default))

    def _trim_content(self, text: str) -> str:
        normalized = (text or "").strip()
        max_chars = self._cfg_int("max_turn_chars", 1200)
        if len(normalized) <= max_chars:
            return normalized
        return normalized[-max_chars:]

    def _select_history(self, history: list[dict[str, str]]) -> list[tuple[str, str]]:
        selected: list[tuple[str, str]] = []
        total_chars = 0
        max_messages = self._cfg_int("max_history_messages", 12)
        max_chars = self._cfg_int("max_history_chars", 6000)

        for item in reversed(history or []):
            role = item.get("role")
            content = self._trim_content(item.get("content", ""))
            if role not in {"user", "assistant"} or not content:
                continue
            if len(selected) >= max_messages:
                break
            if total_chars + len(content) > max_chars:
                break
            selected.append((role, content))
            total_chars += len(content)

        selected.reverse()
        return selected

    def invoke(self, inputs_dict: dict[str, Any], *, model_override: str | None = None) -> dict[str, Any]:
        inputs = self._validate_inputs(inputs_dict)

        try:
            # Render system prompt from prompt.md (keeps prompt editable outside code)
            template = self.prompt_source.get_template() if self.prompt_source else None
            system_text = ""
            if template is not None:
                rendered = render(template, {"user_message": inputs.user_message})
                system_text = rendered.get("system", "").strip()

            messages: list[tuple[str, str]] = []
            if system_text:
                messages.append(("system", system_text))
            messages.extend(self._select_history(inputs.history))
            messages.append(("user", self._trim_content(inputs.user_message)))

            model = model_override or self.model
            if not model:
                raise RuntimeError(f"skill {self.name} has no model configured")
            adapter = self._resolve_adapter(model)
            timeout = self._cfg_float("timeout_seconds", 10.0)
            retries = self._cfg_int("max_retries", 2)

            def _invoke_once() -> tuple[str, str, str]:
                def _run():
                    return adapter.invoke(
                        model=model,
                        messages=messages,
                        constraints={
                            "temperature": self.temperature,
                            "max_output_tokens": self.max_output_tokens,
                        },
                    )

                output = with_timeout(_run, timeout, self.name)
                answer = (output.answer_text or "").strip()
                if not answer:
                    raise ValueError("model returned empty output")
                return answer, adapter.provider, output.finish_reason

            def _is_retryable(error: Exception) -> bool:
                lowered = str(error).lower()
                return not any(m in lowered for m in ("empty output", "bad request", "invalid"))

            answer, provider, finish_reason = call_with_retry(
                operation=_invoke_once,
                max_retries=retries,
                base_delay_seconds=1.0,
                is_retryable=_is_retryable,
            )
            outputs_dict = {"answer": answer, "provider": provider, "finish_reason": finish_reason}

        except SkillValidationError:
            raise
        except Exception as exc:
            outputs_dict = self.fallback(inputs, exc)

        return self._validate_outputs(outputs_dict).model_dump()

    def fallback(self, inputs: Inputs, error: Exception) -> dict[str, Any]:
        return {
            "answer": "Xin lỗi, hệ thống chưa thể trả lời ngay lúc này. Bạn thử lại sau ít phút nhé.",
            "provider": None,
            "finish_reason": "error",
        }
