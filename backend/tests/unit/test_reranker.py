"""Unit tests for result reranker."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.embedding import SentenceTransformerEmbedding
from rag.fts_engine import SearchResult
from rag.reranker import ReRanker


def test_reranker_returns_scored_results():
    embedder = SentenceTransformerEmbedding(dimension=32)
    reranker = ReRanker(embedding_model=embedder)

    docs = [
        SearchResult(id="1", content="deploy with docker", score=0.4, metadata={}),
        SearchResult(id="2", content="oauth2 authentication", score=0.3, metadata={}),
        SearchResult(id="3", content="python unit tests", score=0.2, metadata={}),
    ]

    ranked = reranker.rerank("docker deployment", docs)

    assert len(ranked) == 3
    assert all(0.0 <= d.score <= 1.0 for d in ranked)


def test_reranker_top_n_limit():
    embedder = SentenceTransformerEmbedding(dimension=24)
    reranker = ReRanker(embedding_model=embedder)

    docs = [
        SearchResult(id=str(i), content=f"doc {i}", score=0.1, metadata={})
        for i in range(10)
    ]

    ranked = reranker.rerank("doc", docs, top_n=4)
    assert len(ranked) == 4


def test_reranker_stable_sort_when_scores_equal(monkeypatch):
    embedder = SentenceTransformerEmbedding(dimension=8)
    reranker = ReRanker(embedding_model=embedder)

    docs = [
        SearchResult(id="a", content="A", score=0.0, metadata={}),
        SearchResult(id="b", content="B", score=0.0, metadata={}),
        SearchResult(id="c", content="C", score=0.0, metadata={}),
    ]

    monkeypatch.setattr(reranker, "_score_pair", lambda q, c: 0.5)

    ranked = reranker.rerank("x", docs)
    assert [d.id for d in ranked] == ["a", "b", "c"]
