"""Backward-compat facade over MessageRepository.search_fts and friends.

`SearchResult` is re-exported from models.search so legacy importers
(rag.hybrid_search, rag.retrieval_node, rag.multi_query_retriever, rag.reranker,
api.routers.search) keep working unchanged.

This shim will be removed in step 7 once api/deps.py wires services directly.
"""

from __future__ import annotations

from typing import Any

from db.connection import SQLiteConnectionFactory
from models.search import SearchResult
from repositories.message_repo import MessageRepository

__all__ = ["FTSEngine", "SearchResult"]


class FTSEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._factory = SQLiteConnectionFactory(db_path)
        self._messages = MessageRepository(self._factory)

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return self._messages.search_fts(
            query=query, limit=limit, min_score=min_score, filters=filters
        )

    def index_message(self, message_id: str, content: str) -> None:
        self._messages.fts_index(message_id, content)

    def delete_message(self, message_id: str) -> None:
        self._messages.fts_delete(message_id)

    def rebuild_index(self) -> None:
        self._messages.fts_rebuild()
