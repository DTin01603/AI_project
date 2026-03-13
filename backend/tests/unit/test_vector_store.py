"""Unit tests for vector store."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.embedding import SentenceTransformerEmbedding
from rag.vector_store import ChromaVectorStore


def test_vector_store_add_and_search(tmp_path: Path):
    store = ChromaVectorStore(persist_directory=str(tmp_path / "vs"))
    embedder = SentenceTransformerEmbedding(dimension=32)

    texts = ["deploy with docker", "oauth2 authentication", "python testing"]
    ids = ["m1", "m2", "m3"]
    embeddings = embedder.embed(texts)

    store.add(
        ids=ids,
        embeddings=embeddings,
        texts=texts,
        metadatas=[{"conversation_id": "c1"}] * 3,
    )

    query_vector = embedder.embed_query("docker deploy")
    results = store.search(query_embedding=query_vector, top_k=2)

    assert len(results) == 2
    assert all("id" in row for row in results)
    assert all("score" in row for row in results)


def test_vector_store_filtering(tmp_path: Path):
    store = ChromaVectorStore(persist_directory=str(tmp_path / "vs"))
    embedder = SentenceTransformerEmbedding(dimension=24)

    texts = ["first", "second"]
    ids = ["a", "b"]
    embeddings = embedder.embed(texts)

    store.add(
        ids=ids,
        embeddings=embeddings,
        texts=texts,
        metadatas=[{"source_type": "conversation"}, {"source_type": "document"}],
    )

    query = embedder.embed_query("first")
    results = store.search(query_embedding=query, top_k=5, filters={"source_type": "document"})

    assert len(results) == 1
    assert results[0]["id"] == "b"


def test_vector_store_persist_and_load(tmp_path: Path):
    root = tmp_path / "vs"
    embedder = SentenceTransformerEmbedding(dimension=20)

    store = ChromaVectorStore(persist_directory=str(root), collection_name="test_collection")
    text = "persist me"
    vec = embedder.embed_query(text)
    store.add(ids=["x"], embeddings=[vec], texts=[text], metadatas=[{"k": "v"}])
    store.persist()

    store2 = ChromaVectorStore(persist_directory=str(root), collection_name="test_collection")
    store2.load()

    results = store2.search(query_embedding=vec, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "x"
