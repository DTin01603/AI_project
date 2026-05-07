from __future__ import annotations

from db.connection import SQLiteConnectionFactory
from repositories.conversation_repo import ConversationRepository
from repositories.message_repo import MessageRepository


class ConversationService:
    """Business logic for conversation persistence with transactional guarantees."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        factory: SQLiteConnectionFactory,
    ) -> None:
        self._conversations = conversation_repo
        self._messages = message_repo
        self._factory = factory

    def get_or_create_conversation(self, conversation_id: str | None) -> str:
        return self._conversations.create(conversation_id)

    def persist_turn(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
    ) -> tuple[str | None, str | None]:
        """Save user + assistant messages atomically.

        Returns (user_msg_id, assistant_msg_id). Either may be None if the
        corresponding text was empty (caller already stripped). If insertion
        fails midway, the whole turn is rolled back — no orphan user message.
        """
        self._conversations.create(conversation_id)
        user_id: str | None = None
        assistant_id: str | None = None
        with self._factory.transaction() as conn:
            if user_message:
                user_id = self._messages.insert(
                    conversation_id, "user", user_message, conn=conn
                )
            if assistant_message:
                assistant_id = self._messages.insert(
                    conversation_id, "assistant", assistant_message, conn=conn
                )
        return user_id, assistant_id

    def get_history(self, conversation_id: str) -> list[dict[str, str]]:
        return self._messages.history_dicts(conversation_id)
