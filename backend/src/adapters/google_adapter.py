from langchain_google_genai import ChatGoogleGenerativeAI

from adapters.base import AdapterOutput
from config import settings


class GeminiAdapter:
    provider = "gemini"

    def invoke(
        self,
        *,
        model: str,
        messages: list,
        constraints: dict[str, float | int],
    ) -> AdapterOutput:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        temperature = float(constraints.get("temperature", settings.default_temperature))
        max_output_tokens = int(constraints.get("max_output_tokens", settings.default_max_output_tokens))
        model_name = settings.provider_model_name(model)

        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
            timeout=settings.model_timeout_seconds,
            max_tokens=max_output_tokens,
        )

        response = llm.invoke(messages)
        response_content = response.content

        if isinstance(response_content, list):
            answer_text = "".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in response_content
            ).strip()
        else:
            answer_text = str(response_content or "").strip()

        usage = getattr(response, "usage_metadata", {}) or {}
        response_metadata = getattr(response, "response_metadata", {}) or {}

        return AdapterOutput(
            answer_text=answer_text,
            finish_reason=str(response_metadata.get("finish_reason") or "stop"),
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )
