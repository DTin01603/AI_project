"""Unit tests for contextual compressor."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.contextual_compressor import ContextualCompressor
from rag.embedding import SentenceTransformerEmbedding


def test_contextual_compressor_adds_ellipsis_for_gaps():
    compressor = ContextualCompressor(embedding_model=SentenceTransformerEmbedding(dimension=32))
    text = "Alpha sentence. Beta sentence. Gamma sentence. Delta sentence."

    result = compressor.compress(query="alpha delta", document_text=text, relevance_score=0.25)

    assert result.total_sentences >= 4
    assert result.selected_sentences >= 1
    assert result.compression_ratio <= 0.8
    assert isinstance(result.text, str)


def test_contextual_compressor_preserves_more_for_high_relevance():
    compressor = ContextualCompressor(embedding_model=SentenceTransformerEmbedding(dimension=32))
    text = "One. Two. Three. Four. Five. Six."

    low = compressor.compress(query="one", document_text=text, relevance_score=0.1)
    high = compressor.compress(query="one", document_text=text, relevance_score=0.9)

    assert high.selected_sentences >= low.selected_sentences
    assert 0.2 <= low.compression_ratio <= 0.8
    assert 0.2 <= high.compression_ratio <= 0.8
