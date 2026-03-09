from __future__ import annotations

from typing import Any

from adapters import get_adapter_for_model
from config import settings


def _is_usable_model(model: str) -> bool:
    if not model:
        return False
    normalized = model.strip()
    if normalized in settings.model_registry:
        return settings.is_model_available(normalized)
    return False


def _select_runtime_model(requested_model: str, fallback_model: str | None) -> str:
    requested = requested_model.strip()
    fallback = str(fallback_model or "").strip()

    if _is_usable_model(requested):
        return requested

    if _is_usable_model(fallback):
        return fallback

    if _is_usable_model(settings.default_model):
        return settings.default_model

    available = settings.available_models()
    if available:
        return available[0]

    return requested or fallback


def resolve_and_apply_model(
    metadata: dict[str, Any],
    *components: Any,
    fallback_model: str | None = None,
) -> str:
    """Resolve runtime model from metadata/default and apply to model-aware components."""
    requested_model = str(metadata.get("model") or "").strip()
    model = _select_runtime_model(requested_model, fallback_model)
    if not model:
        return ""

    metadata["model"] = model
    if requested_model and requested_model != model:
        metadata.setdefault("model_runtime", {})
        metadata["model_runtime"].update(
            {
                "requested_model": requested_model,
                "effective_model": model,
                "fallback_applied": True,
            }
        )

    for component in components:
        if component is None:
            continue
        if hasattr(component, "model"):
            setattr(component, "model", model)
        if hasattr(component, "adapter"):
            setattr(component, "adapter", get_adapter_for_model(model))

    return model
