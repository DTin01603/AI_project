"""Unit tests for DocumentIndexingService (step 5 of refactor-architecture).

Covers tasks.md tests for step 5:
- 5.1: index persists DocumentRecord and pushes chunks to vector_store
- 5.2: embedding failure does NOT persist any document row
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from rag.config import RAGConfig
from rag.document_loader import load_document
from repositories.document_repo import DocumentRepository
from services.document_indexing_service import DocumentIndexingService


class _StubVectorStore:
    def __init__(self) -> None:
        self.add_calls: list[dict[str, Any]] = []
        self.persist_calls = 0

    def add(self, *, ids, embeddings, texts, metadatas) -> None:
        self.add_calls.append(
            {"ids": list(ids), "embeddings": list(embeddings), "texts": list(texts), "metadatas": list(metadatas)}
        )

    def persist(self) -> None:
        self.persist_calls += 1

    def search(self, *args, **kwargs):  # pragma: no cover - unused in indexing
        return []


class _StubEmbedding:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("embedding api down")
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


@pytest.fixture
def factory(tmp_path: Path) -> SQLiteConnectionFactory:
    f = SQLiteConnectionFactory(str(tmp_path / "step5.db"))
    run_migrations(f)
    return f


def _write_doc(tmp_path: Path, name: str = "note.md", body: str = "hello world") -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_should_persist_document_and_add_to_vector_store_when_index(
    tmp_path: Path, factory: SQLiteConnectionFactory
) -> None:
    repo = DocumentRepository(factory)
    vs = _StubVectorStore()
    emb = _StubEmbedding()
    service = DocumentIndexingService(
        document_repo=repo,
        embedding_model=emb,
        vector_store=vs,
        config=RAGConfig(chunk_size=128, chunk_overlap=16, chunking_strategy="recursive"),
    )

    file_path = _write_doc(tmp_path, body="this is some indexable content for testing")
    document = load_document(file_path=str(file_path), loaders=service.loaders)

    result = service.index_document(document)

    assert result.chunk_count > 0
    assert vs.persist_calls == 1
    assert len(vs.add_calls) == 1
    assert len(vs.add_calls[0]["ids"]) == result.chunk_count

    record = repo.get(result.document_id)
    assert record is not None
    assert record.file_path == str(file_path)
    assert record.chunk_count == result.chunk_count


def test_should_not_persist_document_when_embedding_fails(
    tmp_path: Path, factory: SQLiteConnectionFactory
) -> None:
    repo = DocumentRepository(factory)
    vs = _StubVectorStore()
    emb = _StubEmbedding(fail=True)
    service = DocumentIndexingService(
        document_repo=repo,
        embedding_model=emb,
        vector_store=vs,
        config=RAGConfig(chunk_size=128, chunk_overlap=16, chunking_strategy="recursive"),
    )

    file_path = _write_doc(tmp_path, body="content that will fail to embed")
    document = load_document(file_path=str(file_path), loaders=service.loaders)

    with pytest.raises(RuntimeError, match="embedding api down"):
        service.index_document(document)

    assert vs.add_calls == []
    assert vs.persist_calls == 0
    assert repo.list_all() == []
