"""Full-text search entry point built on the messages_fts virtual table.

`FTSEngine` is the public API for FTS5 search over conversation messages.
It is a thin orchestration layer over `MessageRepository`, which owns the
actual SQL because the FTS5 virtual table shares triggers with `messages`
— keeping both behind one repository avoids the implicit coupling of two
classes writing to tables that must stay in sync.

The engine accepts an injected `MessageRepository` so the AppContainer
can share its single SQLiteConnectionFactory; callers that don't have
one (e.g. ad-hoc scripts) can build the engine from a `db_path` via the
``from_db_path`` classmethod.
"""

from __future__ import annotations

from typing import Any

from db.connection import SQLiteConnectionFactory
from models.search import SearchResult
from repositories.message_repo import MessageRepository

__all__ = ["FTSEngine", "SearchResult"]


class FTSEngine:
    def __init__(self, message_repo: MessageRepository) -> None:
        self._messages = message_repo
        self._factory = message_repo._factory

    @classmethod
    def from_db_path(cls, db_path: str) -> "FTSEngine":
        """Build an FTSEngine from a SQLite path. Convenient for scripts/tests."""
        factory = SQLiteConnectionFactory(db_path)
        return cls(MessageRepository(factory))

    @property
    def db_path(self) -> str:
        return self._factory.db_path

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
