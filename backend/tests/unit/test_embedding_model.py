"""Unit tests for embedding models."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.embedding import SentenceTransformerEmbedding


def test_embedding_dimension_consistency():
    model = SentenceTransformerEmbedding(dimension=64, cache_size=100)

    vectors = model.embed(["hello", "world", "hello"])

    assert len(vectors) == 3
    assert all(len(v) == 64 for v in vectors)


def test_embedding_is_deterministic_for_same_input():
    model = SentenceTransformerEmbedding(dimension=32, cache_size=100)

    v1 = model.embed_query("deterministic test")
    v2 = model.embed_query("deterministic test")

    assert v1 == v2


def test_embedding_chunking_over_token_limit():
    model = SentenceTransformerEmbedding(dimension=48, token_limit=4)

    text = "one two three four five six seven eight"
    vector = model.embed_query(text)

    assert len(vector) == 48


def test_embedding_normalized_vectors():
    model = SentenceTransformerEmbedding(dimension=16, normalize=True)

    vector = model.embed_query("normalization test")
    norm = sum(v * v for v in vector) ** 0.5

    # Allow tiny floating point tolerance
    assert 0.999 <= norm <= 1.001
