from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models.document import DocumentRecord, IndexingResult
from rag.chunking import Chunk, ChunkingStrategy, CodeAwareChunking, RecursiveCharacterChunking
from rag.config import RAGConfig
from rag.document_loader import (
    Document,
    DocumentLoadError,
    DocumentLoader,
    get_default_loaders,
    load_document,
)
from rag.embedding import EmbeddingModel
from rag.vector_store import VectorStore
from repositories.document_repo import DocumentRepository


logger = logging.getLogger(__name__)


class DocumentIndexingService:
    """Index external documents into a vector store + persist metadata row."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        config: RAGConfig | None = None,
        loaders: list[DocumentLoader] | None = None,
        chunking_strategy: ChunkingStrategy | None = None,
    ) -> None:
        self._documents = document_repo
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.config = config or RAGConfig()
        self.loaders = loaders or get_default_loaders()
        self.chunking_strategy = chunking_strategy or self._resolve_chunking_strategy(self.config)

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

        record = DocumentRecord(
            id=document_id,
            file_path=document.metadata.file_path,
            file_name=document.metadata.file_name,
            source_type=document.source_type,
            file_size=document.metadata.file_size,
            created_at=document.metadata.created_at,
            modified_at=document.metadata.modified_at,
            indexed_at=datetime.now(timezone.utc).isoformat(),
            chunk_count=len(chunks),
            metadata=dict(document.metadata.extra),
        )
        self._documents.upsert(record)

        return IndexingResult(
            document_id=document_id,
            file_path=document.metadata.file_path,
            source_type=document.source_type,
            chunk_count=len(chunks),
        )

    def index_files(
        self, file_paths: list[str | Path]
    ) -> tuple[list[IndexingResult], list[tuple[str, str]]]:
        results: list[IndexingResult] = []
        errors: list[tuple[str, str]] = []
        for file_path in file_paths:
            try:
                results.append(self.index_file(file_path))
            except Exception as exc:
                path = str(file_path)
                logger.exception("Failed to index file: %s", path)
                errors.append((path, str(exc)))
        return results, errors

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

    @staticmethod
    def _build_chunk_metadata(chunk: Chunk, document: Document) -> dict[str, Any]:
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
