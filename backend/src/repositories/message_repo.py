from __future__ import annotations

import sqlite3
from typing import Any
from uuid import uuid4

from db.connection import SQLiteConnectionFactory
from models.conversation import Message
from models.search import SearchResult
from repositories._base import utc_now_iso


class MessageRepository:
    """CRUD on `messages` plus FTS5 search on `messages_fts`.

    The two tables share a cluster (FTS triggers keep them in sync), so
    keeping them behind one repository avoids the implicit coupling that
    existed when FTSEngine was a separate class.
    """

    def __init__(self, factory: SQLiteConnectionFactory) -> None:
        self._factory = factory

    # ------------------------------------------------------------------ writes

    def insert(
        self,
        conversation_id: str,
        role: str,
        content: str,
        *,
        conn: sqlite3.Connection | None = None,
    ) -> str:
        message_id = str(uuid4())
        now = utc_now_iso()
        sql = (
            "INSERT INTO messages (id, conversation_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)"
        )
        params = (message_id, conversation_id, role, content, now)
        if conn is not None:
            conn.execute(sql, params)
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            return message_id
        with self._factory.connect() as inner:
            inner.execute(sql, params)
            inner.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
        return message_id

    # ------------------------------------------------------------------ reads

    def list_by_conversation(self, conversation_id: str) -> list[Message]:
        with self._factory.connect() as conn:
            rows = conn.execute(
                "SELECT id, conversation_id, role, content, created_at "
                "FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,),
            ).fetchall()
        return [
            Message(
                id=str(row["id"]),
                conversation_id=str(row["conversation_id"]),
                role=str(row["role"]),
                content=str(row["content"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    def history_dicts(self, conversation_id: str) -> list[dict[str, str]]:
        """Legacy projection used by Database.get_conversation_history."""
        with self._factory.connect() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM messages "
                "WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,),
            ).fetchall()
        return [
            {
                "role": str(row["role"]),
                "content": str(row["content"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------ FTS

    def search_fts(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        if not query or not query.strip():
            return []

        filters = filters or {}
        sql_parts = [
            "SELECT m.id, m.content, m.conversation_id, m.role, m.created_at, "
            "bm25(messages_fts) as raw_score "
            "FROM messages m "
            "JOIN messages_fts ON m.id = messages_fts.message_id "
            "WHERE messages_fts MATCH ?"
        ]
        params: list[Any] = [query]

        if "conversation_id" in filters:
            sql_parts.append("AND m.conversation_id = ?")
            params.append(filters["conversation_id"])

        if "date_range" in filters:
            start_date, end_date = filters["date_range"]
            sql_parts.append("AND m.created_at BETWEEN ? AND ?")
            params.extend([start_date, end_date])

        sql_parts.append("ORDER BY raw_score DESC LIMIT ?")
        params.append(limit)
        sql = " ".join(sql_parts)

        with self._factory.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        if not rows:
            return []

        raw_scores = [row["raw_score"] for row in rows]
        min_raw = min(raw_scores)
        max_raw = max(raw_scores)
        score_range = max_raw - min_raw if max_raw != min_raw else 1.0

        results: list[SearchResult] = []
        for row in rows:
            normalized = (
                (row["raw_score"] - min_raw) / score_range if score_range > 0 else 1.0
            )
            if normalized < min_score:
                continue
            results.append(
                SearchResult(
                    id=str(row["id"]),
                    content=str(row["content"]),
                    score=normalized,
                    metadata={
                        "conversation_id": str(row["conversation_id"]),
                        "role": str(row["role"]),
                        "created_at": str(row["created_at"]),
                    },
                    source_type="conversation",
                )
            )
        return results

    def fts_index(self, message_id: str, content: str) -> None:
        with self._factory.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO messages_fts(message_id, content) "
                "VALUES (?, ?)",
                (message_id, content),
            )

    def fts_delete(self, message_id: str) -> None:
        with self._factory.connect() as conn:
            conn.execute(
                "DELETE FROM messages_fts WHERE message_id = ?", (message_id,)
            )

    def fts_rebuild(self) -> None:
        with self._factory.connect() as conn:
            conn.execute("DELETE FROM messages_fts")
            conn.execute(
                "INSERT INTO messages_fts(message_id, content) "
                "SELECT id, content FROM messages"
            )
            conn.execute("INSERT INTO messages_fts(messages_fts) VALUES('optimize')")
