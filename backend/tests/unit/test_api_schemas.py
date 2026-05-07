"""Unit tests for api/schemas/ DTOs (step 8 of refactor-architecture).

Covers tasks.md tests for step 8:
- 8.1: ChatRequest accepts a valid payload
- 8.2: ChatRequest raises pydantic.ValidationError on empty message
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.schemas.chat import ChatRequest, ChatResponse, ResponseMeta
from api.schemas.search import (
    HealthResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)


def test_should_validate_chat_request_payload_when_pydantic_parses() -> None:
    payload = {"conversation_id": "c-1", "message": "hi"}
    req = ChatRequest(**payload)

    assert req.message == "hi"
    assert req.conversation_id == "c-1"


def test_should_raise_validation_error_when_message_is_empty() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(conversation_id="c-1", message="")


def test_should_validate_chat_response_when_meta_provided() -> None:
    resp = ChatResponse(
        request_id="r-1",
        conversation_id="c-1",
        status="ok",
        answer="hello",
        meta=ResponseMeta(provider="gemini", model="gemini-2.5-flash", finish_reason="stop"),
    )
    assert resp.status == "ok"
    assert resp.meta.provider == "gemini"


def test_should_validate_search_request_payload() -> None:
    req = SearchRequest(query="docker", method="hybrid", top_k=3)
    assert req.query == "docker"
    assert req.method == "hybrid"
    assert req.top_k == 3


def test_should_raise_validation_error_when_search_query_is_blank() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query="   ")


def test_should_build_search_response_with_items() -> None:
    item = SearchResultItem(
        id="m-1", content="hello world", score=0.9, source_type="conversation"
    )
    resp = SearchResponse(
        results=[item], total_count=1, query="hi", method="fts", execution_time_ms=12.3
    )
    assert resp.results[0].id == "m-1"
    assert resp.total_count == 1


def test_should_build_health_response() -> None:
    h = HealthResponse(status="ok", fts_available=True, timestamp="2026-05-07T00:00:00+00:00")
    assert h.status == "ok"
    assert h.fts_available is True
