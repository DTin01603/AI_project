"""Unit tests for query expansion."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.query_expander import QueryExpander


def test_query_expander_returns_original_and_alternatives():
    expander = QueryExpander(max_expansions=3, timeout_ms=200)

    queries = expander.expand("auth api")

    assert len(queries) >= 3
    assert queries[0] == "auth api"
    assert len({q.lower() for q in queries}) == len(queries)


def test_query_expander_uses_cache_for_same_query():
    expander = QueryExpander(max_expansions=2, timeout_ms=200)

    first = expander.expand("deploy service")
    second = expander.expand("deploy service")

    assert first == second


def test_query_expander_handles_empty_query():
    expander = QueryExpander()

    assert expander.expand("   ") == []
