"""Smoke tests for api/schemas/ DTOs (step 8 of refactor-architecture).

Pydantic itself is well-tested upstream, so we only verify the bits that
are *our* contract: the field names + the validation rules we add on top
(chat `message` must be non-empty, search `query` must not be whitespace).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.schemas.chat import ChatRequest
from api.schemas.search import SearchRequest


def test_should_validate_chat_request_payload_when_pydantic_parses() -> None:
    req = ChatRequest(conversation_id="c-1", message="hi")
    assert req.message == "hi"
    assert req.conversation_id == "c-1"


def test_should_raise_validation_error_when_chat_message_is_empty() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(conversation_id="c-1", message="")


def test_should_raise_validation_error_when_search_query_is_blank() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query="   ")
