"""Integration tests for Phase 2b retrieval methods."""

import sys
import tempfile
from pathlib import Path

from langchain_core.messages import HumanMessage

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.config import RAGConfig
from rag.fts_engine import FTSEngine
from agent.nodes.retrieval_node import RetrievalNode
from agent.database import Database
from services.retrieval_service import RetrievalService


def _build_node(db_path: str, config: RAGConfig) -> RetrievalNode:
    service = RetrievalService(fts_engine=FTSEngine(db_path), config=config)
    return RetrievalNode(service=service)


def test_retrieval_node_hybrid_method_end_to_end(tmp_path: Path):
    db_path = str(tmp_path / "hybrid.db")
    db = Database(db_path)

    conv = db.create_conversation()
    db.save_message(conv, "user", "How to deploy with Docker?")
    db.save_message(conv, "assistant", "Use docker compose in production.")
    db.save_message(conv, "user", "How to secure API with OAuth2?")

    node = _build_node(db_path, RAGConfig(default_search_method="hybrid", default_top_k=3))

    out = node({"messages": [HumanMessage(content="docker deploy")]})

    assert out["retrieved_documents"]
    assert out["retrieval_metadata"]["method"] == "hybrid"


def test_retrieval_node_vector_method_explicit(tmp_path: Path):
    db_path = str(tmp_path / "vector.db")
    db = Database(db_path)

    conv = db.create_conversation()
    db.save_message(conv, "user", "JWT authentication for API")
    db.save_message(conv, "assistant", "Use access and refresh tokens")

    node = _build_node(db_path, RAGConfig(default_search_method="vector", default_top_k=3))

    docs = node.retrieve(query="JWT tokens", method="vector", top_k=3, min_score=0.0)

    assert isinstance(docs, list)
    assert len(docs) > 0
    assert all(0.0 <= d.score <= 1.0 for d in docs)
