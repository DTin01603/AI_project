from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    locale: str | None = None
    channel: str | None = None
    model: str | None = None


class ResponseError(BaseModel):
    code: str
    message: str


class ResponseMeta(BaseModel):
    provider: str | None = None
    model: str | None = None
    finish_reason: str | None = None


class ChatResponse(BaseModel):
    request_id: str
    conversation_id: str | None = None
    status: Literal["ok", "error"]
    answer: str
    sources: list[str] = []
    error: ResponseError | None = None
    meta: ResponseMeta
