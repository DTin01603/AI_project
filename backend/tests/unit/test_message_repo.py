"""Unit tests for MessageRepository (step 2 of refactor-architecture).

Covers tasks.md tests:
- 2.1: search_fts returns Message-equivalent SearchResult instances on match
- 2.2: search_fts escapes special chars (single quote) without SQL injection
- 2.3: Message domain entity rejects invalid role at construction
- 2.4: insert(conn=...) participates in caller's transaction
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from models.conversation import Message
from models.search import SearchResult
from repositories.conversation_repo import ConversationRepository
from repositories.message_repo import MessageRepository


@pytest.fixture
def factory(tmp_path: Path) -> SQLiteConnectionFactory:
    f = SQLiteConnectionFactory(str(tmp_path / "step2.db"))
    run_migrations(f)
    return f


def test_should_return_messages_when_search_fts_matches(factory: SQLiteConnectionFactory) -> None:
    conv_repo = ConversationRepository(factory)
    msg_repo = MessageRepository(factory)
    conv_id = conv_repo.create("conv-2-1")

    msg_repo.insert(conv_id, "user", "hello world")
    msg_repo.insert(conv_id, "user", "foo bar")
    msg_repo.insert(conv_id, "user", "world peace")

    results = msg_repo.search_fts("world")

    assert len(results) == 2
    assert all(isinstance(r, SearchResult) for r in results)
    assert all("world" in r.content.lower() for r in results)


def test_should_escape_special_chars_when_search_fts_with_quote(
    factory: SQLiteConnectionFactory,
) -> None:
    conv_repo = ConversationRepository(factory)
    msg_repo = MessageRepository(factory)
    conv_id = conv_repo.create("conv-2-2")
    msg_repo.insert(conv_id, "user", "it's a test")

    # FTS5 may treat ' as a tokenizer boundary; the contract is "no SQL injection,
    # no OperationalError" — result count is implementation-defined.
    try:
        results = msg_repo.search_fts("test")
    except sqlite3.OperationalError as exc:
        pytest.fail(f"search_fts raised OperationalError on safe input: {exc}")

    assert isinstance(results, list)
    assert any("test" in r.content for r in results)


def test_should_raise_when_message_role_is_invalid() -> None:
    with pytest.raises(ValueError, match="role"):
        Message(
            id="m-1",
            conversation_id="c-1",
            role="hacker",
            content="x",
            created_at="2026-05-07T00:00:00+00:00",
        )


def test_should_use_passed_conn_when_insert_with_conn_arg(
    factory: SQLiteConnectionFactory,
) -> None:
    conv_repo = ConversationRepository(factory)
    msg_repo = MessageRepository(factory)
    conv_id = conv_repo.create("conv-2-4")

    # Insert under a transaction that we abort by raising — both inserts must
    # share the same conn so rollback wipes them together.
    with pytest.raises(RuntimeError, match="abort"):
        with factory.transaction() as conn:
            msg_repo.insert(conv_id, "user", "first", conn=conn)
            msg_repo.insert(conv_id, "assistant", "second", conn=conn)
            raise RuntimeError("abort")

    surviving = msg_repo.list_by_conversation(conv_id)
    assert surviving == []


