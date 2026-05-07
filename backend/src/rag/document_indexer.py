"""Backward-compat facade over DocumentIndexingService + DocumentRepository.

Public API (`DocumentIndexer`, `IndexingResult`) is preserved so existing
callers (scripts/index_doc.py, integration tests, rag/__init__.py exports)
keep working.

Logic now lives in:
- models/document.py (DocumentRecord + IndexingResult)
- repositories/document_repo.py (SQL)
- services/document_indexing_service.py (chunk + embed + persist)

This shim will be removed in step 7 once api/deps.py wires services directly.
"""

from __future__ import annotations

from pathlib import Path

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from models.document import IndexingResult
from rag.chunking import ChunkingStrategy
from rag.config import RAGConfig
from rag.document_loader import Document, DocumentLoader
from rag.embedding import EmbeddingModel
from rag.vector_store import VectorStore
from repositories.document_repo import DocumentRepository
from services.document_indexing_service import DocumentIndexingService

__all__ = ["DocumentIndexer", "IndexingResult"]


class DocumentIndexer:
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
        self._factory = SQLiteConnectionFactory(db_path)
        run_migrations(self._factory)
        self._repo = DocumentRepository(self._factory)
        self._service = DocumentIndexingService(
            document_repo=self._repo,
            embedding_model=embedding_model,
            vector_store=vector_store,
            config=config,
            loaders=loaders,
            chunking_strategy=chunking_strategy,
        )
        # Re-expose service attributes some callers may read.
        self.embedding_model = self._service.embedding_model
        self.vector_store = self._service.vector_store
        self.config = self._service.config
        self.loaders = self._service.loaders
        self.chunking_strategy = self._service.chunking_strategy

    def index_file(self, file_path: str | Path) -> IndexingResult:
        return self._service.index_file(file_path)

    def index_document(self, document: Document) -> IndexingResult:
        return self._service.index_document(document)

    def index_files(
        self, file_paths: list[str | Path]
    ) -> tuple[list[IndexingResult], list[tuple[str, str]]]:
        return self._service.index_files(file_paths)
