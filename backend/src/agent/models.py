from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class ResearchTask(BaseModel):
    order: int
    query: str
    goal: str


class ResearchResult(BaseModel):
    task_order: int
    extracted_information: str
    sources: list[str]
    success: bool = True
    error: str | None = None


class MessageRecord(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    request_id: str
    conversation_id: str
    answer: str
    sources: list[str] = []
    status: Literal["ok", "error"] = "ok"
    error: str | None = None
