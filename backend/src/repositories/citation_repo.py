from __future__ import annotations

import json
import sqlite3

from db.connection import SQLiteConnectionFactory
from models.citation import Citation
from repositories._base import utc_now_iso


class CitationRepository:
    def __init__(self, factory: SQLiteConnectionFactory) -> None:
        self._factory = factory

    def upsert(self, citation: Citation, *, conn: sqlite3.Connection | None = None) -> None:
        sql = """
            INSERT INTO citations (
                citation_id, document_id, chunk_id, source_type, title,
                author, created_at, metadata_json, available, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(citation_id) DO UPDATE SET
                document_id=excluded.document_id,
                chunk_id=excluded.chunk_id,
                source_type=excluded.source_type,
                title=excluded.title,
                author=excluded.author,
                created_at=excluded.created_at,
                metadata_json=excluded.metadata_json,
                available=excluded.available,
                updated_at=excluded.updated_at
        """
        params = (
            citation.citation_id,
            citation.document_id,
            citation.chunk_id,
            citation.source_type,
            citation.title,
            citation.author,
            citation.created_at,
            json.dumps(citation.metadata),
            1 if citation.available else 0,
            utc_now_iso(),
        )
        if conn is not None:
            conn.execute(sql, params)
            return
        with self._factory.connect() as inner:
            inner.execute(sql, params)

    def get(self, citation_id: str) -> Citation | None:
        with self._factory.connect() as conn:
            row = conn.execute(
                "SELECT citation_id, document_id, chunk_id, source_type, title, "
                "author, created_at, metadata_json, available "
                "FROM citations WHERE citation_id = ?",
                (citation_id,),
            ).fetchone()
        if row is None:
            return None
        return Citation(
            citation_id=str(row["citation_id"]),
            document_id=str(row["document_id"]),
            chunk_id=str(row["chunk_id"]) if row["chunk_id"] else None,
            source_type=str(row["source_type"]),
            title=str(row["title"]),
            author=str(row["author"]) if row["author"] else None,
            created_at=str(row["created_at"]) if row["created_at"] else None,
            metadata=json.loads(str(row["metadata_json"])) if row["metadata_json"] else {},
            available=bool(row["available"]),
        )

    def soft_delete(self, citation_id: str) -> None:
        with self._factory.connect() as conn:
            conn.execute(
                "UPDATE citations SET available = 0 WHERE citation_id = ?",
                (citation_id,),
            )

    def insert_usage(
        self,
        citation_id: str,
        query: str,
        used_in_response: bool,
        *,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        sql = (
            "INSERT INTO citation_usage (citation_id, query, used_in_response, used_at) "
            "VALUES (?, ?, ?, ?)"
        )
        params = (citation_id, query, 1 if used_in_response else 0, utc_now_iso())
        if conn is not None:
            conn.execute(sql, params)
            return
        with self._factory.connect() as inner:
            inner.execute(sql, params)
