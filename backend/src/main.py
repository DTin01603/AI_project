import logging
from datetime import datetime, timezone
from time import perf_counter
import sys
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.routers import chat_v2_router, core_router


def configure_logging() -> None:
    # Configure global logging format/levels for app and uvicorn loggers.
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("app.request").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def create_app() -> FastAPI:
    # Build FastAPI application and register middleware + exception handlers + routers.
    configure_logging()
    application = FastAPI(title="Simple Agent API", version="0.1.0")
    application.state.started_at = datetime.now(timezone.utc)
    request_logger = logging.getLogger("app.request")
    request_logger.setLevel(logging.INFO)

    @application.middleware("http")
    async def log_http_requests(request: Request, call_next):
        # Log every HTTP request latency and status for observability.
        started_at = perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (perf_counter() - started_at) * 1000
            log_line = (
                f"{request.method} {request.url.path} "
                f"status={response.status_code} duration_ms={duration_ms:.2f}"
            )
            request_logger.info(log_line)
            print(f"[request] {log_line}", flush=True)
            return response
        except Exception as error:
            duration_ms = (perf_counter() - started_at) * 1000
            log_line = (
                f"{request.method} {request.url.path} "
                f"status=500 duration_ms={duration_ms:.2f} error={error}"
            )
            request_logger.exception(log_line)
            print(f"[request] {log_line}", flush=True)
            raise

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, _: RequestValidationError):
        # Return unified API error payload for request validation failures.
        request_id = request.headers.get("x-request-id") or str(uuid4())
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "conversation_id": None,
                "status": "error",
                "answer": "",
                "sources": [],
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Request data is invalid",
                },
                "meta": {
                    "provider": None,
                    "model": None,
                    "finish_reason": None,
                },
            },
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _: Exception):
        # Return unified API error payload for unhandled server errors.
        request_id = request.headers.get("x-request-id") or str(uuid4())
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "conversation_id": None,
                "status": "error",
                "answer": "",
                "sources": [],
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                },
                "meta": {
                    "provider": None,
                    "model": None,
                    "finish_reason": None,
                },
            },
        )

    application.include_router(core_router)
    application.include_router(chat_v2_router)

    return application


app = create_app()

__all__ = [
    "app",
    "create_app",
]
