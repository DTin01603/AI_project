"""Unit tests for hybrid search engine."""

import sys
import tempfile
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.embedding import SentenceTransformerEmbedding
from rag.fts_engine import FTSEngine
from rag.hybrid_search import HybridSearchEngine
from rag.vector_store import ChromaVectorStore
from research_agent.database import Database


def _setup_db() -> tuple[str, FTSEngine]:
    temp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = temp.name
    temp.close()

    db = Database(db_path)
    conv = db.create_conversation()
    db.save_message(conv, "user", "deploy with docker compose")
    db.save_message(conv, "assistant", "oauth2 authentication flow")
    db.save_message(conv, "assistant", "unit testing with pytest")

    return db_path, FTSEngine(db_path)


def test_hybrid_search_returns_ranked_results(tmp_path: Path):
    db_path, fts = _setup_db()
    embedder = SentenceTransformerEmbedding(dimension=32)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "vs"))

    # Bootstrap vector store from DB messages for test simplicity.
    db = Database(db_path)
    with db._connect() as conn:
        rows = conn.execute("SELECT id, content, conversation_id, role, created_at FROM messages").fetchall()

    ids = [str(r["id"]) for r in rows]
    texts = [str(r["content"]) for r in rows]
    metas = [
        {
            "conversation_id": str(r["conversation_id"]),
            "role": str(r["role"]),
            "created_at": str(r["created_at"]),
            "source_type": "conversation",
        }
        for r in rows
    ]
    store.add(ids=ids, embeddings=embedder.embed(texts), texts=texts, metadatas=metas)

    engine = HybridSearchEngine(fts_engine=fts, vector_store=store, embedding_model=embedder)
    results = engine.search("docker deploy", top_k=3)

    assert len(results) > 0
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_hybrid_search_deduplicates_results(tmp_path: Path):
    db_path, fts = _setup_db()
    embedder = SentenceTransformerEmbedding(dimension=16)
    store = ChromaVectorStore(persist_directory=str(tmp_path / "vs"))

    db = Database(db_path)
    with db._connect() as conn:
        rows = conn.execute("SELECT id, content FROM messages").fetchall()

    ids = [str(r["id"]) for r in rows]
    texts = [str(r["content"]) for r in rows]
    store.add(ids=ids, embeddings=embedder.embed(texts), texts=texts, metadatas=[{} for _ in ids])

    engine = HybridSearchEngine(fts_engine=fts, vector_store=store, embedding_model=embedder)
    results = engine.search("authentication", top_k=10)

    returned_ids = [r.id for r in results]
    assert len(returned_ids) == len(set(returned_ids))
