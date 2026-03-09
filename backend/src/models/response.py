from typing import Literal

from pydantic import BaseModel


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
