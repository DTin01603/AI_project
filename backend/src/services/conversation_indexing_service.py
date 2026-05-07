from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from rag.embedding import EmbeddingModel
from rag.vector_store import VectorStore
from repositories.message_repo import MessageRepository
from services.conversation_service import ConversationService


logger = logging.getLogger(__name__)


class ConversationIndexingService:
    """Save a conversation message to SQLite and embed it into the vector store.

    SQLite write goes through ConversationService (FTS index updated by trigger);
    embedding + vector store push happen after. Embedding/vector failures are
    logged but do not roll back the SQLite save — the message is the source of
    truth, vector index is best-effort.
    """

    def __init__(
        self,
        conversation_service: ConversationService,
        message_repo: MessageRepository,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        chunk_size: int = 512,
    ) -> None:
        self._conversation_service = conversation_service
        self._messages = message_repo
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.chunk_size = max(64, chunk_size)

    def create_conversation(self, conversation_id: str | None = None) -> str:
        return self._conversation_service.get_or_create_conversation(conversation_id)

    def get_conversation_history(self, conversation_id: str) -> list[dict[str, str]]:
        return self._conversation_service.get_history(conversation_id)

    def save_message(self, conversation_id: str, role: str, content: str) -> str:
        # Step 1: persist message to SQLite (FTS trigger keeps fts table in sync).
        self._conversation_service.get_or_create_conversation(conversation_id)
        message_id = self._messages.insert(conversation_id, role, content)

        # Step 2: chunk content for vector indexing.
        chunks = self._chunk_content(content)

        # Step 3: embed chunks (best-effort).
        try:
            embeddings = self.embedding_model.embed(chunks)
        except Exception as exc:
            logger.error(
                "Failed to embed message %s: %s", message_id, exc, exc_info=True
            )
            return message_id

        # Step 4: push embeddings to vector store (best-effort).
        now = datetime.now(timezone.utc).isoformat()
        ids = [f"{message_id}::chunk::{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "role": role,
                "created_at": now,
                "source_type": "conversation",
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]
        try:
            self.vector_store.add(
                ids=ids,
                embeddings=embeddings,
                texts=chunks,
                metadatas=metadatas,
            )
            self.vector_store.persist()
            logger.debug(
                "Indexed message %s with %d chunks into vector store",
                message_id,
                len(chunks),
            )
        except Exception as exc:
            logger.error(
                "Failed to index message %s in vector store: %s",
                message_id,
                exc,
                exc_info=True,
            )
        return message_id

    def _chunk_content(self, content: str) -> list[str]:
        if not content or len(content) <= self.chunk_size:
            return [content]

        sentences = re.split(r"(?<=[.!?])\s+", content)
        chunks: list[str] = []
        current: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length > self.chunk_size and current:
                chunks.append(" ".join(current))
                current = []
                current_length = 0
            current.append(sentence)
            current_length += sentence_length + 1

        if current:
            chunks.append(" ".join(current))
        return chunks if chunks else [content]
