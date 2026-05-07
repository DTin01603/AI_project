"""Unit tests for ConversationIndexingService (step 6 of refactor-architecture).

Covers tasks.md tests for step 6:
- 6.1: save_message indexes the message into vector_store
- 6.2: SQLite write succeeds even when vector_store / embedding fails
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from repositories.conversation_repo import ConversationRepository
from repositories.message_repo import MessageRepository
from services.conversation_indexing_service import ConversationIndexingService
from services.conversation_service import ConversationService


class _StubVectorStore:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.add_calls: list[dict[str, Any]] = []
        self.persist_calls = 0

    def add(self, *, ids, embeddings, texts, metadatas) -> None:
        if self.fail:
            raise RuntimeError("vector store down")
        self.add_calls.append(
            {"ids": list(ids), "embeddings": list(embeddings), "texts": list(texts), "metadatas": list(metadatas)}
        )

    def persist(self) -> None:
        self.persist_calls += 1


class _StubEmbedding:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.fail:
            raise RuntimeError("embedding api down")
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


def _make_service(tmp_path: Path, *, vs_fail=False, emb_fail=False, chunk_size=512):
    factory = SQLiteConnectionFactory(str(tmp_path / "step6.db"))
    run_migrations(factory)
    conv_repo = ConversationRepository(factory)
    msg_repo = MessageRepository(factory)
    conv_service = ConversationService(conv_repo, msg_repo, factory)
    vs = _StubVectorStore(fail=vs_fail)
    emb = _StubEmbedding(fail=emb_fail)
    service = ConversationIndexingService(
        conversation_service=conv_service,
        message_repo=msg_repo,
        embedding_model=emb,
        vector_store=vs,
        chunk_size=chunk_size,
    )
    return service, conv_service, vs


def test_should_index_message_when_save_message_called(tmp_path: Path) -> None:
    service, conv_service, vs = _make_service(tmp_path)
    conv_id = service.create_conversation("conv-6-1")

    msg_id = service.save_message(conv_id, "user", "How does docker volume work?")

    # SQLite verified via ConversationService.get_history
    history = conv_service.get_history(conv_id)
    assert len(history) == 1
    assert history[0]["content"] == "How does docker volume work?"

    # Vector store called once with chunks linked back to the message id
    assert len(vs.add_calls) == 1
    assert vs.persist_calls == 1
    add = vs.add_calls[0]
    assert all(cid.startswith(f"{msg_id}::chunk::") for cid in add["ids"])
    assert all(meta["message_id"] == msg_id for meta in add["metadatas"])
    assert all(meta["conversation_id"] == conv_id for meta in add["metadatas"])
    assert all(meta["role"] == "user" for meta in add["metadatas"])


def test_should_persist_to_sqlite_even_when_embedding_fails(tmp_path: Path) -> None:
    service, conv_service, vs = _make_service(tmp_path, emb_fail=True)
    conv_id = service.create_conversation("conv-6-2")

    msg_id = service.save_message(conv_id, "user", "still saved on embedding failure")

    assert msg_id
    history = conv_service.get_history(conv_id)
    assert len(history) == 1
    assert history[0]["content"] == "still saved on embedding failure"
    # Embedding failed before vector_store.add was reached.
    assert vs.add_calls == []


def test_should_persist_to_sqlite_even_when_vector_store_fails(tmp_path: Path) -> None:
    service, conv_service, _ = _make_service(tmp_path, vs_fail=True)
    conv_id = service.create_conversation("conv-6-3")

    msg_id = service.save_message(conv_id, "user", "vector store may be down")

    assert msg_id
    history = conv_service.get_history(conv_id)
    assert len(history) == 1


def test_should_chunk_long_message_when_exceeds_chunk_size(tmp_path: Path) -> None:
    service, _, vs = _make_service(tmp_path, chunk_size=80)
    conv_id = service.create_conversation("conv-6-4")
    long_content = " ".join([f"This is sentence number {i}." for i in range(20)])

    service.save_message(conv_id, "user", long_content)

    add = vs.add_calls[0]
    assert len(add["ids"]) > 1, "Long message should be split into multiple chunks"
    total = add["metadatas"][0]["total_chunks"]
    assert total == len(add["ids"])
