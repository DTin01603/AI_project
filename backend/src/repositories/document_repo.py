from __future__ import annotations

import json
import sqlite3

from db.connection import SQLiteConnectionFactory
from models.document import DocumentRecord


class DocumentRepository:
    def __init__(self, factory: SQLiteConnectionFactory) -> None:
        self._factory = factory

    def upsert(
        self, record: DocumentRecord, *, conn: sqlite3.Connection | None = None
    ) -> None:
        sql = """
            INSERT INTO documents (
                id, file_path, file_name, source_type, file_size,
                created_at, modified_at, indexed_at, chunk_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                file_path = excluded.file_path,
                file_name = excluded.file_name,
                source_type = excluded.source_type,
                file_size = excluded.file_size,
                created_at = excluded.created_at,
                modified_at = excluded.modified_at,
                indexed_at = excluded.indexed_at,
                chunk_count = excluded.chunk_count,
                metadata_json = excluded.metadata_json
        """
        params = (
            record.id,
            record.file_path,
            record.file_name,
            record.source_type,
            record.file_size,
            record.created_at,
            record.modified_at,
            record.indexed_at,
            record.chunk_count,
            json.dumps(record.metadata),
        )
        if conn is not None:
            conn.execute(sql, params)
            return
        with self._factory.connect() as inner:
            inner.execute(sql, params)

    def get(self, document_id: str) -> DocumentRecord | None:
        with self._factory.connect() as conn:
            row = conn.execute(
                "SELECT id, file_path, file_name, source_type, file_size, "
                "created_at, modified_at, indexed_at, chunk_count, metadata_json "
                "FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_all(self) -> list[DocumentRecord]:
        with self._factory.connect() as conn:
            rows = conn.execute(
                "SELECT id, file_path, file_name, source_type, file_size, "
                "created_at, modified_at, indexed_at, chunk_count, metadata_json "
                "FROM documents ORDER BY indexed_at DESC"
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def _row_to_record(row) -> DocumentRecord:
        return DocumentRecord(
            id=str(row["id"]),
            file_path=str(row["file_path"]),
            file_name=str(row["file_name"]),
            source_type=str(row["source_type"]),
            file_size=int(row["file_size"]),
            created_at=str(row["created_at"]),
            modified_at=str(row["modified_at"]),
            indexed_at=str(row["indexed_at"]),
            chunk_count=int(row["chunk_count"]),
            metadata=json.loads(str(row["metadata_json"])) if row["metadata_json"] else {},
        )
