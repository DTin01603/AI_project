"""Integration test: AppContainer wires factory -> repos -> ConversationService
correctly so that persist_turn writes both messages atomically into a real
SQLite database (no mocks).

This is the end-to-end gate verifying the step 1-7a wiring is correct
together (factory + migrations + repos + service + container).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from api.deps import AppContainer, get_container


@pytest.fixture(autouse=True)
def _clear_container_cache():
    get_container.cache_clear()
    yield
    get_container.cache_clear()


def test_app_container_persist_turn_writes_both_messages(tmp_path: Path) -> None:
    db_path = str(tmp_path / "integration.db")
    container = AppContainer(db_path=db_path)

    conv_id = container.conversation_service.get_or_create_conversation(None)
    user_id, assistant_id = container.conversation_service.persist_turn(
        conv_id, "ping", "pong"
    )

    assert user_id and assistant_id
    history = container.conversation_service.get_history(conv_id)
    assert [h["role"] for h in history] == ["user", "assistant"]
    assert [h["content"] for h in history] == ["ping", "pong"]

    # Cross-check via the message repository directly — confirms repo and
    # service both read/write the same physical rows.
    messages = container.message_repo.list_by_conversation(conv_id)
    assert len(messages) == 2
