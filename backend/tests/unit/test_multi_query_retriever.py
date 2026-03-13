"""Unit tests for multi-query retrieval."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.fts_engine import SearchResult
from rag.multi_query_retriever import MultiQueryRetriever


def _fake_search(query: str, top_k: int, min_score: float, filters: dict | None):
    mapping = {
        "authentication": [
            SearchResult(id="a", content="OAuth2 authentication", score=0.7, metadata={}, source_type="conversation"),
            SearchResult(id="x", content="General security", score=0.4, metadata={}, source_type="document"),
        ],
        "rate limiting": [
            SearchResult(id="b", content="API rate limiting", score=0.6, metadata={}, source_type="document"),
            SearchResult(id="a", content="OAuth2 authentication", score=0.65, metadata={}, source_type="conversation"),
        ],
    }
    return mapping.get(query, [])[:top_k]


def test_multi_query_decomposition_rule_based():
    retriever = MultiQueryRetriever(search_fn=_fake_search)

    sub = retriever.decompose("authentication and rate limiting?")

    assert len(sub) >= 2
    assert "authentication" in [x.lower() for x in sub]


def test_multi_query_aggregation_and_boost():
    retriever = MultiQueryRetriever(search_fn=_fake_search)

    rows = retriever.retrieve("authentication and rate limiting", top_k=5)

    assert len(rows) >= 2
    top = rows[0].result
    assert top.id == "a"
    assert top.metadata["sub_query_count"] >= 2
    assert top.score > 0.7
