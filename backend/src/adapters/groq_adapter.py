import os
from typing import Any

from groq import Groq

from adapters.base import AdapterOutput
from config import settings

try:
    from langsmith import traceable
except Exception:  # pragma: no cover - optional dependency at runtime
    traceable = None


def _is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _langsmith_manual_tracing_enabled() -> bool:
    if traceable is None:
        return False
    if not os.getenv("LANGSMITH_API_KEY", "").strip():
        return False
    return _is_truthy_env("LANGSMITH_TRACING") or _is_truthy_env("LANGCHAIN_TRACING_V2")


class GroqAdapter:
    provider = "groq"

    @staticmethod
    def _extract_response_payload(response: Any) -> dict[str, Any]:
        choice = response.choices[0] if response.choices else None
        message = choice.message if choice else None
        answer_text = str(getattr(message, "content", "") or "").strip()

        usage = response.usage
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        finish_reason = getattr(choice, "finish_reason", "stop") if choice else "stop"

        return {
            "answer_text": answer_text,
            "finish_reason": str(finish_reason or "stop"),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
        }

    def _create_completion_with_optional_trace(
        self,
        *,
        client: Groq,
        model: str,
        model_name: str,
        normalized_messages: list[dict[str, str]],
        temperature: float,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        def _execute(
            *,
            traced_model: str,
            traced_model_name: str,
            traced_messages: list[dict[str, str]],
            traced_temperature: float,
            traced_max_output_tokens: int,
        ) -> dict[str, Any]:
            response = client.chat.completions.create(
                model=traced_model_name,
                messages=traced_messages,
                temperature=traced_temperature,
                max_tokens=traced_max_output_tokens,
            )
            return self._extract_response_payload(response)

        if _langsmith_manual_tracing_enabled():
            traced_execute = traceable(name="groq.chat.completions", run_type="llm")(_execute)
            return traced_execute(
                traced_model=model,
                traced_model_name=model_name,
                traced_messages=normalized_messages,
                traced_temperature=temperature,
                traced_max_output_tokens=max_output_tokens,
            )

        return _execute(
            traced_model=model,
            traced_model_name=model_name,
            traced_messages=normalized_messages,
            traced_temperature=temperature,
            traced_max_output_tokens=max_output_tokens,
        )

    def invoke(
        self,
        *,
        model: str,
        messages: list,
        constraints: dict[str, float | int],
    ) -> AdapterOutput:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not configured")

        temperature = float(constraints.get("temperature", settings.default_temperature))
        max_output_tokens = int(constraints.get("max_output_tokens", settings.default_max_output_tokens))
        model_name = settings.provider_model_name(model)

        client = Groq(api_key=settings.groq_api_key, timeout=settings.model_timeout_seconds)
        normalized_messages = [
            {
                "role": str(role),
                "content": str(content),
            }
            for role, content in messages
        ]
        payload = self._create_completion_with_optional_trace(
            client=client,
            model=model,
            model_name=model_name,
            normalized_messages=normalized_messages,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        return AdapterOutput(
            answer_text=str(payload.get("answer_text", "") or "").strip(),
            finish_reason=str(payload.get("finish_reason", "stop") or "stop"),
            input_tokens=int(payload.get("input_tokens", 0) or 0),
            output_tokens=int(payload.get("output_tokens", 0) or 0),
        )
