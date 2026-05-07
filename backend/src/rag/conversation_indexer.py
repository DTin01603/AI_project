"""Backward-compat facade over ConversationIndexingService.

Public API (`ConversationIndexer(database, embedding_model, vector_store, chunk_size)`,
`save_message`, `create_conversation`, `get_conversation_history`, `db_path`)
is preserved so existing callers (api/deps.py, integration/unit tests) keep
working.

Logic now lives in services/conversation_indexing_service.py.

This shim will be removed in step 7 once api/deps.py wires services directly.
"""

from __future__ import annotations

from rag.embedding import EmbeddingModel
from rag.vector_store import VectorStore
from repositories.conversation_repo import ConversationRepository
from repositories.message_repo import MessageRepository
from research_agent.database import Database
from services.conversation_indexing_service import ConversationIndexingService
from services.conversation_service import ConversationService

__all__ = ["ConversationIndexer"]


class ConversationIndexer:
    def __init__(
        self,
        database: Database,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        chunk_size: int = 512,
    ) -> None:
        self.database = database
        factory = database._factory
        conv_repo = ConversationRepository(factory)
        msg_repo = MessageRepository(factory)
        conversation_service = ConversationService(conv_repo, msg_repo, factory)
        self._service = ConversationIndexingService(
            conversation_service=conversation_service,
            message_repo=msg_repo,
            embedding_model=embedding_model,
            vector_store=vector_store,
            chunk_size=chunk_size,
        )
        # Re-expose so tests / callers reading these attrs keep working.
        self.embedding_model = self._service.embedding_model
        self.vector_store = self._service.vector_store
        self.chunk_size = self._service.chunk_size

    def save_message(self, conversation_id: str, role: str, content: str) -> str:
        return self._service.save_message(conversation_id, role, content)

    def create_conversation(self, conversation_id: str | None = None) -> str:
        return self._service.create_conversation(conversation_id)

    def get_conversation_history(self, conversation_id: str) -> list[dict[str, str]]:
        return self._service.get_conversation_history(conversation_id)

    @property
    def db_path(self) -> str:
        return self.database.db_path
