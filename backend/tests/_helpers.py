"""Shared test helpers (test infra only — not production code).

Tests historically used `Database(db_path).save_message(...)` to seed
fixture data. After the Database shim was removed, equivalent setup
needs `SQLiteConnectionFactory + run_migrations + repos`, which is too
verbose to inline in every test. The helper below packages that boilerplate.
"""

from __future__ import annotations

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from repositories.conversation_repo import ConversationRepository
from repositories.message_repo import MessageRepository


class TestDb:
    """Lightweight fixture wrapper for seeding conversation+message rows.

    NOT a production type — only used to keep test setup short. Deliberately
    avoids implementing higher-level service operations: tests that need
    transactional behaviour should build a real ConversationService.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.factory = SQLiteConnectionFactory(db_path)
        run_migrations(self.factory)
        self.conversations = ConversationRepository(self.factory)
        self.messages = MessageRepository(self.factory)

    def create_conversation(self, conversation_id: str | None = None) -> str:
        return self.conversations.create(conversation_id)

    def save_message(self, conversation_id: str, role: str, content: str) -> str:
        # Mirror the previous Database.save_message behaviour: ensure the
        # conversation row exists, then insert the message.
        self.conversations.create(conversation_id)
        return self.messages.insert(conversation_id, role, content)

    def get_conversation_history(self, conversation_id: str) -> list[dict[str, str]]:
        return self.messages.history_dicts(conversation_id)


__all__ = ["TestDb"]
