"""Integration tests for query expansion through RetrievalNode/HybridSearchEngine."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.config import RAGConfig
from rag.fts_engine import FTSEngine
from rag.retrieval_node import RetrievalNode
from research_agent.database import Database


def test_retrieval_node_hybrid_query_expansion_metadata(tmp_path: Path):
    db_path = str(tmp_path / "qe.db")
    db = Database(db_path)

    conv = db.create_conversation()
    db.save_message(conv, "assistant", "Use OAuth2 authentication for API security")

    node = RetrievalNode(
        fts_engine=FTSEngine(db_path),
        config=RAGConfig(
            default_search_method="hybrid",
            enable_query_expansion=True,
            query_expansion_count=2,
            default_top_k=5,
            min_relevance_score=0.0,
        ),
    )

    # Make expansion deterministic for this test.
    node.query_expander.expand = lambda query, max_alternatives=None: [query, "authentication"]

    docs = node.retrieve(query="login", method="hybrid", top_k=5, min_score=0.0)

    assert len(docs) > 0
    assert any("matched_queries" in doc.metadata for doc in docs)
