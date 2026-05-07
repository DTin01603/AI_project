"""Unit tests for ConversationRepository (step 2 of refactor-architecture)."""

from __future__ import annotations

from pathlib import Path

import pytest

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from repositories.conversation_repo import ConversationRepository


@pytest.fixture
def factory(tmp_path: Path) -> SQLiteConnectionFactory:
    f = SQLiteConnectionFactory(str(tmp_path / "conv.db"))
    run_migrations(f)
    return f


def test_should_generate_id_when_create_called_without_arg(factory: SQLiteConnectionFactory) -> None:
    repo = ConversationRepository(factory)
    cid = repo.create()
    assert cid
    assert repo.get(cid) is not None


def test_should_reuse_id_when_create_called_with_existing_id(factory: SQLiteConnectionFactory) -> None:
    repo = ConversationRepository(factory)

    cid1 = repo.create("explicit-id")
    cid2 = repo.create("explicit-id")

    assert cid1 == cid2 == "explicit-id"
    # Idempotent: only one row exists.
    with factory.connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE id = ?", ("explicit-id",)
        ).fetchone()[0]
    assert count == 1


def test_should_return_none_when_get_unknown_id(factory: SQLiteConnectionFactory) -> None:
    repo = ConversationRepository(factory)
    assert repo.get("does-not-exist") is None
