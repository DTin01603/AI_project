"""Unit tests for HybridSearchEngine query expansion path."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.embedding import EmbeddingModel
from rag.fts_engine import SearchResult
from rag.hybrid_search import HybridSearchEngine
from rag.query_expander import QueryExpander
from rag.vector_store import VectorStore


class _DummyEmbedding(EmbeddingModel):
    @property
    def dimension(self) -> int:
        return 3

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


class _DummyVectorStore(VectorStore):
    def add(self, ids, embeddings, texts, metadatas=None):
        return None

    def search(self, query_embedding, top_k=10, filters=None):
        return []

    def delete(self, ids):
        return None

    def persist(self):
        return None

    def load(self):
        return None


class _DummyFTS:
    def search(self, query, limit=10, min_score=0.0, filters=None):
        if "authentication" in query:
            return [
                SearchResult(
                    id="doc-1",
                    content="OAuth2 authentication flow",
                    score=0.9,
                    metadata={"source_type": "conversation"},
                    source_type="conversation",
                )
            ]
        return []


class _StubExpander(QueryExpander):
    def __init__(self):
        pass

    def expand(self, query: str, max_alternatives: int | None = None) -> list[str]:
        return [query, "authentication flow"]


def test_hybrid_search_with_query_expansion_enabled():
    engine = HybridSearchEngine(
        fts_engine=_DummyFTS(),
        vector_store=_DummyVectorStore(),
        embedding_model=_DummyEmbedding(),
        query_expander=_StubExpander(),
    )

    rows = engine.search(
        query="login",
        top_k=5,
        min_score=0.0,
        enable_query_expansion=True,
        query_expansion_count=2,
    )

    assert len(rows) == 1
    assert rows[0].id == "doc-1"
    assert "matched_queries" in rows[0].metadata


def test_hybrid_search_with_query_expansion_disabled():
    engine = HybridSearchEngine(
        fts_engine=_DummyFTS(),
        vector_store=_DummyVectorStore(),
        embedding_model=_DummyEmbedding(),
        query_expander=_StubExpander(),
    )

    rows = engine.search(
        query="login",
        top_k=5,
        min_score=0.0,
        enable_query_expansion=False,
    )

    assert rows == []
