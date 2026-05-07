"""LLM adapter registry with lazy SDK import.

Optional vendor SDKs (groq, google-genai) are not imported at module load
time so that `import adapters` works in environments where some SDKs are
not installed. The actual SDK is imported only when an adapter for that
provider is resolved at runtime.
"""

from __future__ import annotations

import importlib
from typing import Callable

from adapters.base import BaseAdapter


def _load_gemini_adapter() -> type[BaseAdapter]:
    module = importlib.import_module("adapters.google_adapter")
    return module.GeminiAdapter


def _load_groq_adapter() -> type[BaseAdapter]:
    module = importlib.import_module("adapters.groq_adapter")
    return module.GroqAdapter


# Provider key -> loader returning the adapter class. Loader runs only when
# the adapter is requested, so the SDK import happens lazily.
_REGISTRY: dict[str, Callable[[], type[BaseAdapter]]] = {
    "gemini": _load_gemini_adapter,
    "google": _load_gemini_adapter,
    "groq": _load_groq_adapter,
}


def list_providers() -> list[str]:
    """List registered provider keys without importing any SDK."""
    return sorted(_REGISTRY.keys())


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

    loader = _REGISTRY.get(provider)
    if loader is None:
        raise ValueError(f"unsupported model provider: {provider}")
    adapter_cls = loader()
    return adapter_cls()


__all__ = ["BaseAdapter", "get_adapter_for_model", "list_providers"]
