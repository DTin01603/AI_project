from adapters.base import BaseAdapter
from adapters.google_adapter import GeminiAdapter
from adapters.groq_adapter import GroqAdapter


def get_adapter_for_model(model: str) -> BaseAdapter:
	normalized = (model or "").strip().lower()
	if "/" in normalized:
		provider = normalized.split("/", 1)[0]
	elif normalized.startswith("gemini"):
		provider = "gemini"
	elif normalized.startswith(("llama", "mixtral", "qwen")):
		provider = "groq"
	else:
		provider = "gemini"

	if provider == "groq":
		return GroqAdapter()
	if provider in {"gemini", "google"}:
		return GeminiAdapter()
	raise ValueError(f"unsupported model provider: {provider}")


__all__ = ["BaseAdapter", "GeminiAdapter", "GroqAdapter", "get_adapter_for_model"]
