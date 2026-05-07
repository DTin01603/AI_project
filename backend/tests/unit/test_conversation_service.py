"""Unit tests for ConversationService.persist_turn (step 3 of refactor-architecture).

Covers tasks.md tests:
- 3.1: persist_turn writes both messages on success
- 3.2: rollback on assistant insert failure leaves zero messages (atomic)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from repositories.conversation_repo import ConversationRepository
from repositories.message_repo import MessageRepository
from services.conversation_service import ConversationService


@pytest.fixture
def service_with_factory(tmp_path: Path):
    factory = SQLiteConnectionFactory(str(tmp_path / "step3.db"))
    run_migrations(factory)
    conv_repo = ConversationRepository(factory)
    msg_repo = MessageRepository(factory)
    service = ConversationService(conv_repo, msg_repo, factory)
    return service, msg_repo, factory


def test_should_persist_both_messages_when_persist_turn_succeeds(
    service_with_factory,
) -> None:
    service, msg_repo, _ = service_with_factory
    conv_id = service.get_or_create_conversation("conv-3-1")

    user_id, assistant_id = service.persist_turn(conv_id, "hi", "hello there")

    assert user_id and assistant_id
    rows = msg_repo.list_by_conversation(conv_id)
    assert [r.role for r in rows] == ["user", "assistant"]
    assert [r.content for r in rows] == ["hi", "hello there"]


def test_should_rollback_user_message_when_assistant_insert_fails(
    service_with_factory,
) -> None:
    service, msg_repo, factory = service_with_factory
    conv_id = service.get_or_create_conversation("conv-3-2")

    # Patch insert so the SECOND call (assistant) raises after the first (user)
    # has already touched the same conn — the transaction must roll the user
    # message back too.
    original_insert = msg_repo.insert
    call_count = {"n": 0}

    def flaky_insert(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise sqlite3.IntegrityError("boom")
        return original_insert(*args, **kwargs)

    msg_repo.insert = flaky_insert  # type: ignore[assignment]

    with pytest.raises(sqlite3.IntegrityError, match="boom"):
        service.persist_turn(conv_id, "user msg", "assistant msg")

    msg_repo.insert = original_insert  # type: ignore[assignment]

    surviving = msg_repo.list_by_conversation(conv_id)
    assert surviving == [], (
        "User message must be rolled back when assistant insert fails"
    )


def test_should_skip_empty_user_message_when_persist_turn(
    service_with_factory,
) -> None:
    service, msg_repo, _ = service_with_factory
    conv_id = service.get_or_create_conversation("conv-3-3")

    user_id, assistant_id = service.persist_turn(conv_id, "", "only assistant")

    assert user_id is None
    assert assistant_id is not None
    rows = msg_repo.list_by_conversation(conv_id)
    assert len(rows) == 1
    assert rows[0].role == "assistant"


def test_should_return_history_when_get_history_called(
    service_with_factory,
) -> None:
    service, _, _ = service_with_factory
    conv_id = service.get_or_create_conversation("conv-3-4")
    service.persist_turn(conv_id, "q1", "a1")
    service.persist_turn(conv_id, "q2", "a2")

    history = service.get_history(conv_id)

    assert [h["role"] for h in history] == ["user", "assistant", "user", "assistant"]
    assert [h["content"] for h in history] == ["q1", "a1", "q2", "a2"]
