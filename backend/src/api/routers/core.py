from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config import settings

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    # Liveness endpoint with process uptime.
    started_at = getattr(request.app.state, "started_at", datetime.now(timezone.utc))
    uptime_seconds = (datetime.now(timezone.utc) - started_at).total_seconds()

    return {
        "status": "ok",
        "uptime_seconds": uptime_seconds,
    }


@router.get("/ready")
def ready() -> JSONResponse:
    # Readiness endpoint based on whether at least one model provider is available.
    available_models = len(settings.available_models())
    if available_models > 0:
        return JSONResponse(
            status_code=200,
            content={"status": "ready", "available_models": available_models},
        )
    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "available_models": 0,
            "reason": "No available model provider",
        },
    )


@router.get("/models")
def models() -> dict[str, object]:
    # Expose configured model registry and runtime availability flags.
    return {
        "models": [
            {
                "name": model,
                "provider": settings.model_provider(model),
                "available": settings.is_model_available(model),
            }
            for model in settings.model_registry
        ]
    }
