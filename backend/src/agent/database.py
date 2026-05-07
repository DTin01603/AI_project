"""Backward-compat facade over ConversationRepository + MessageRepository.

Public API (`create_conversation`, `save_message`, `get_conversation_history`,
`db_path`, `_connect`) is preserved so existing callers and tests keep working.
This shim will be removed in step 7 once api/deps.py wires services directly.
"""

from __future__ import annotations

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from repositories.conversation_repo import ConversationRepository
from repositories.message_repo import MessageRepository


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._factory = SQLiteConnectionFactory(db_path)
        run_migrations(self._factory)
        self._conversations = ConversationRepository(self._factory)
        self._messages = MessageRepository(self._factory)

    def _connect(self):
        return self._factory.connect()

    def create_conversation(self, conversation_id: str | None = None) -> str:
        return self._conversations.create(conversation_id)

    def save_message(self, conversation_id: str, role: str, content: str) -> str:
        self._conversations.create(conversation_id)
        return self._messages.insert(conversation_id, role, content)

    def get_conversation_history(self, conversation_id: str) -> list[dict[str, str]]:
        return self._messages.history_dicts(conversation_id)
