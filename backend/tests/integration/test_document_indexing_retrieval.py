"""Integration tests for Phase 2c document indexing and multi-source retrieval."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.config import RAGConfig
from rag.document_indexer import DocumentIndexer
from rag.embedding import SentenceTransformerEmbedding
from rag.fts_engine import FTSEngine
from rag.retrieval_node import RetrievalNode
from rag.vector_store import ChromaVectorStore
from research_agent.database import Database


def test_document_indexing_and_source_filtering(tmp_path: Path):
    db_path = str(tmp_path / "rag.db")
    db = Database(db_path)

    conversation_id = db.create_conversation()
    db.save_message(conversation_id, "user", "How to deploy using docker compose?")
    db.save_message(conversation_id, "assistant", "Use docker compose up -d")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    document_file = docs_dir / "ops-guide.md"
    document_file.write_text("Docker deployment checklist and rollback procedure.", encoding="utf-8")

    code_file = docs_dir / "deploy.py"
    code_file.write_text(
        "def deploy_with_docker():\n    return 'docker compose up -d'\n", encoding="utf-8"
    )

    embedding = SentenceTransformerEmbedding(dimension=32)
    conversation_store = ChromaVectorStore(
        persist_directory=str(tmp_path / "vs"),
        collection_name="conversation_messages",
    )
    document_store = ChromaVectorStore(
        persist_directory=str(tmp_path / "vs"),
        collection_name="indexed_documents",
    )

    indexer = DocumentIndexer(
        db_path=db_path,
        embedding_model=embedding,
        vector_store=document_store,
        config=RAGConfig(chunk_size=128, chunk_overlap=16, chunking_strategy="recursive"),
    )

    results, errors = indexer.index_files([document_file, code_file])
    assert len(errors) == 0
    assert len(results) == 2

    node = RetrievalNode(
        fts_engine=FTSEngine(db_path),
        embedding_model=embedding,
        vector_store=conversation_store,
        document_vector_store=document_store,
        config=RAGConfig(default_search_method="hybrid", default_top_k=5, min_relevance_score=0.0),
    )

    all_sources = node.retrieve(
        query="docker deploy",
        method="hybrid",
        top_k=10,
        min_score=0.0,
    )
    assert len(all_sources) > 0
    assert any(doc.source_type in {"document", "code_file"} for doc in all_sources)

    only_documents = node.retrieve(
        query="docker deploy",
        method="hybrid",
        top_k=10,
        min_score=0.0,
        filters={"source_types": ["document", "code_file"]},
    )
    assert len(only_documents) > 0
    assert all(doc.source_type in {"document", "code_file"} for doc in only_documents)

    only_conversation = node.retrieve(
        query="docker deploy",
        method="hybrid",
        top_k=10,
        min_score=0.0,
        filters={"source_type": "conversation"},
    )
    assert len(only_conversation) > 0
    assert all(doc.source_type == "conversation" for doc in only_conversation)
