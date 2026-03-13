"""Integration tests for advanced retrieval features in RetrievalNode."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.config import RAGConfig
from rag.fts_engine import FTSEngine
from rag.retrieval_node import RetrievalNode
from research_agent.database import Database


def test_retrieval_node_adds_citations_when_enabled(tmp_path: Path):
    db_path = str(tmp_path / "advanced.db")
    db = Database(db_path)

    conv = db.create_conversation()
    db.save_message(conv, "assistant", "Use OAuth2 and JWT for API security.")

    node = RetrievalNode(
        fts_engine=FTSEngine(db_path),
        config=RAGConfig(
            default_search_method="hybrid",
            enable_query_expansion=False,
            enable_multi_query=False,
            enable_citations=True,
            enable_compression=False,
            min_relevance_score=0.0,
        ),
    )

    docs = node.retrieve(query="oauth2 security", method="hybrid", top_k=5, min_score=0.0)

    assert len(docs) > 0
    assert all("citation_id" in d.metadata for d in docs)


def test_retrieval_node_compression_when_enabled(tmp_path: Path):
    db_path = str(tmp_path / "compress.db")
    db = Database(db_path)

    conv = db.create_conversation()
    db.save_message(
        conv,
        "assistant",
        "Sentence one about deployment. Sentence two about docker compose. "
        "Sentence three about rollback. Sentence four about monitoring.",
    )

    node = RetrievalNode(
        fts_engine=FTSEngine(db_path),
        config=RAGConfig(
            default_search_method="hybrid",
            enable_query_expansion=False,
            enable_multi_query=False,
            enable_citations=False,
            enable_compression=True,
            min_relevance_score=0.0,
        ),
    )

    docs = node.retrieve(query="docker deployment", method="hybrid", top_k=5, min_score=0.0)

    assert len(docs) > 0
    assert all("compression" in d.metadata for d in docs)
