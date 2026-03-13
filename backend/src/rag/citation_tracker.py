"""Citation creation, formatting, and usage tracking."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class Citation:
    """Citation metadata for a retrieved source."""

    citation_id: str
    document_id: str
    chunk_id: str | None
    source_type: str
    title: str
    author: str | None
    created_at: str | None
    metadata: dict[str, Any]
    available: bool = True


class CitationTracker:
    """Tracks citation metadata and usage for retrieved content."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def create_citation(
        self,
        document_id: str,
        chunk_id: str | None,
        source_type: str,
        title: str,
        author: str | None,
        created_at: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> Citation:
        metadata = metadata or {}
        citation_id = self._stable_citation_id(document_id, chunk_id)

        citation = Citation(
            citation_id=citation_id,
            document_id=document_id,
            chunk_id=chunk_id,
            source_type=source_type,
            title=title,
            author=author,
            created_at=created_at,
            metadata=metadata,
            available=True,
        )

        self._upsert_citation(citation)
        return citation

    def format_citation(self, citation: Citation, style: str = "APA") -> str:
        style_upper = style.upper()
        year = self._year(citation.created_at)
        author = citation.author or "Unknown"

        if style_upper == "MLA":
            return f"{author}. \"{citation.title}\". {year}. [{citation.citation_id}]"
        if style_upper == "CHICAGO":
            return f"{author}. {year}. {citation.title}. Citation ID: {citation.citation_id}."

        # Default APA
        return f"{author} ({year}). {citation.title}. [{citation.citation_id}]"

    def track_usage(self, citation_id: str, query: str, used_in_response: bool = True) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO citation_usage (citation_id, query, used_in_response, used_at)
                VALUES (?, ?, ?, ?)
                """,
                (citation_id, query, 1 if used_in_response else 0, self._now_iso()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_citation(self, citation_id: str) -> Citation | None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                """
                SELECT citation_id, document_id, chunk_id, source_type, title, author, created_at, metadata_json, available
                FROM citations
                WHERE citation_id = ?
                """,
                (citation_id,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        import json

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
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("UPDATE citations SET available = 0 WHERE citation_id = ?", (citation_id,))
            conn.commit()
        finally:
            conn.close()

    def get_source_document(self, citation_id: str) -> dict[str, Any] | None:
        citation = self.get_citation(citation_id)
        if citation is None:
            return None
        return {
            "citation_id": citation.citation_id,
            "document_id": citation.document_id,
            "chunk_id": citation.chunk_id,
            "source_type": citation.source_type,
            "title": citation.title,
            "available": citation.available,
            "metadata": citation.metadata,
        }

    def _ensure_schema(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS citations (
                    citation_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_id TEXT,
                    source_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    author TEXT,
                    created_at TEXT,
                    metadata_json TEXT,
                    available INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS citation_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    citation_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    used_in_response INTEGER NOT NULL,
                    used_at TEXT NOT NULL,
                    FOREIGN KEY(citation_id) REFERENCES citations(citation_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_citation_usage_citation ON citation_usage(citation_id)")
            conn.commit()
        finally:
            conn.close()

    def _upsert_citation(self, citation: Citation) -> None:
        import json

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
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
                """,
                (
                    citation.citation_id,
                    citation.document_id,
                    citation.chunk_id,
                    citation.source_type,
                    citation.title,
                    citation.author,
                    citation.created_at,
                    json.dumps(citation.metadata),
                    1 if citation.available else 0,
                    self._now_iso(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _stable_citation_id(document_id: str, chunk_id: str | None) -> str:
        seed = f"{document_id}::{chunk_id or ''}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _year(created_at: str | None) -> str:
        if not created_at:
            return "n.d."
        return created_at[:4]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
