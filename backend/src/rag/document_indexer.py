"""Document indexing pipeline: load -> chunk -> embed -> vector store."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rag.chunking import Chunk, ChunkingStrategy, CodeAwareChunking, RecursiveCharacterChunking
from rag.config import RAGConfig
from rag.document_loader import Document, DocumentLoadError, DocumentLoader, get_default_loaders, load_document
from rag.embedding import EmbeddingModel
from rag.vector_store import VectorStore


logger = logging.getLogger(__name__)


@dataclass
class IndexingResult:
    """Result summary for one document indexing operation."""

    document_id: str
    file_path: str
    source_type: str
    chunk_count: int


class DocumentIndexer:
    """Index external documents into a dedicated vector index."""

    def __init__(
        self,
        db_path: str,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        config: RAGConfig | None = None,
        loaders: list[DocumentLoader] | None = None,
        chunking_strategy: ChunkingStrategy | None = None,
    ) -> None:
        self.db_path = db_path
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.config = config or RAGConfig()
        self.loaders = loaders or get_default_loaders()
        self.chunking_strategy = chunking_strategy or self._resolve_chunking_strategy(self.config)

        self._ensure_schema()

    @staticmethod
    def _resolve_chunking_strategy(config: RAGConfig) -> ChunkingStrategy:
        if config.chunking_strategy == "code-aware":
            return CodeAwareChunking(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
            )
        return RecursiveCharacterChunking(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    def index_file(self, file_path: str | Path) -> IndexingResult:
        document = load_document(file_path=file_path, loaders=self.loaders)
        return self.index_document(document)

    def index_document(self, document: Document) -> IndexingResult:
        if not document.text.strip():
            raise DocumentLoadError(f"Document is empty: {document.metadata.file_path}")

        document_id = self._document_id(document)
        document.id = document_id

        chunks = self.chunking_strategy.chunk(document)
        if not chunks:
            raise DocumentLoadError(f"No chunks generated: {document.metadata.file_path}")

        ids = [chunk.id for chunk in chunks]
        texts = [chunk.text for chunk in chunks]
        metadatas = [self._build_chunk_metadata(chunk, document) for chunk in chunks]
        embeddings = self.embedding_model.embed(texts)

        self.vector_store.add(ids=ids, embeddings=embeddings, texts=texts, metadatas=metadatas)
        self.vector_store.persist()

        self._upsert_document_metadata(document=document, chunk_count=len(chunks))

        return IndexingResult(
            document_id=document_id,
            file_path=document.metadata.file_path,
            source_type=document.source_type,
            chunk_count=len(chunks),
        )

    def index_files(self, file_paths: list[str | Path]) -> tuple[list[IndexingResult], list[tuple[str, str]]]:
        results: list[IndexingResult] = []
        errors: list[tuple[str, str]] = []

        for file_path in file_paths:
            try:
                result = self.index_file(file_path)
                results.append(result)
            except Exception as exc:
                path = str(file_path)
                logger.exception("Failed to index file: %s", path)
                errors.append((path, str(exc)))

        return results, errors

    def _build_chunk_metadata(self, chunk: Chunk, document: Document) -> dict[str, Any]:
        return {
            **chunk.metadata,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "start_offset": chunk.start_offset,
            "end_offset": chunk.end_offset,
            "source_type": document.source_type,
            "title": document.metadata.file_name,
            "file_name": document.metadata.file_name,
            "file_path": document.metadata.file_path,
            "created_at": document.metadata.created_at,
            "modified_at": document.metadata.modified_at,
        }

    def _ensure_schema(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_modified_at ON documents(modified_at)"
            )
            conn.commit()
        finally:
            conn.close()

    def _upsert_document_metadata(self, document: Document, chunk_count: int) -> None:
        import json

        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
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
                """,
                (
                    document.id,
                    document.metadata.file_path,
                    document.metadata.file_name,
                    document.source_type,
                    document.metadata.file_size,
                    document.metadata.created_at,
                    document.metadata.modified_at,
                    now,
                    chunk_count,
                    json.dumps(document.metadata.extra),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _document_id(document: Document) -> str:
        payload = "|".join(
            [
                document.metadata.file_path,
                document.metadata.modified_at,
                document.text,
                document.source_type,
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
