from __future__ import annotations

from uuid import uuid4

from db.connection import SQLiteConnectionFactory
from models.conversation import Conversation
from repositories._base import utc_now_iso


class ConversationRepository:
    def __init__(self, factory: SQLiteConnectionFactory) -> None:
        self._factory = factory

    def create(self, conversation_id: str | None = None) -> str:
        resolved_id = conversation_id or str(uuid4())
        now = utc_now_iso()
        with self._factory.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, created_at, updated_at) "
                "VALUES (?, ?, ?)",
                (resolved_id, now, now),
            )
        return resolved_id

    def touch(self, conversation_id: str, *, conn=None) -> None:
        sql = "UPDATE conversations SET updated_at = ? WHERE id = ?"
        params = (utc_now_iso(), conversation_id)
        if conn is not None:
            conn.execute(sql, params)
            return
        with self._factory.connect() as inner:
            inner.execute(sql, params)

    def get(self, conversation_id: str) -> Conversation | None:
        with self._factory.connect() as conn:
            row = conn.execute(
                "SELECT id, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        return Conversation(
            id=str(row["id"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
