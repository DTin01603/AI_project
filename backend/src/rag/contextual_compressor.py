"""Contextual compression for retrieved documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag.embedding import EmbeddingModel


@dataclass
class CompressionResult:
    """Compression payload including output and ratio diagnostics."""

    text: str
    compression_ratio: float
    selected_sentences: int
    total_sentences: int


class ContextualCompressor:
    """Compress document text by selecting query-relevant sentences."""

    def __init__(self, embedding_model: EmbeddingModel) -> None:
        self.embedding_model = embedding_model

    def compress(
        self,
        query: str,
        document_text: str,
        relevance_score: float,
        min_ratio: float = 0.2,
        max_ratio: float = 0.8,
    ) -> CompressionResult:
        sentences = self._split_sentences(document_text)
        if not sentences:
            return CompressionResult(text=document_text, compression_ratio=1.0, selected_sentences=0, total_sentences=0)

        if len(sentences) == 1:
            return CompressionResult(text=sentences[0], compression_ratio=1.0, selected_sentences=1, total_sentences=1)

        bounded_min = max(0.2, min(0.8, min_ratio))
        bounded_max = max(bounded_min, min(0.8, max_ratio))
        target_ratio = bounded_min + ((bounded_max - bounded_min) * max(0.0, min(1.0, relevance_score)))

        sentence_scores = self._score_sentences(query, sentences)
        target_count = max(1, int(round(len(sentences) * target_ratio)))

        ranked_indices = sorted(range(len(sentences)), key=lambda idx: sentence_scores[idx], reverse=True)
        selected = sorted(ranked_indices[:target_count])

        compressed = self._compose_with_ellipsis(sentences, selected)
        ratio = max(0.0, min(1.0, len(selected) / max(1, len(sentences))))

        return CompressionResult(
            text=compressed,
            compression_ratio=ratio,
            selected_sentences=len(selected),
            total_sentences=len(sentences),
        )

    def _score_sentences(self, query: str, sentences: list[str]) -> list[float]:
        query_vec = self.embedding_model.embed_query(query)
        sentence_vecs = self.embedding_model.embed(sentences)

        scores: list[float] = []
        for idx, vec in enumerate(sentence_vecs):
            base = self._cosine(query_vec, vec)
            # Slight position bias: retain local flow around relevant regions.
            position_bias = 0.02 * (1.0 - (idx / max(1, len(sentence_vecs) - 1)))
            scores.append(max(0.0, min(1.0, base + position_bias)))

        return scores

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        normalized = text.replace("\r\n", "\n").strip()
        if not normalized:
            return []
        # Keep sentence punctuation for readability.
        parts = re.split(r"(?<=[.!?])\s+", normalized)
        cleaned = [p.strip() for p in parts if p and p.strip()]
        return cleaned

    @staticmethod
    def _compose_with_ellipsis(sentences: list[str], selected_indices: list[int]) -> str:
        if not selected_indices:
            return ""

        output: list[str] = []
        previous = None
        for idx in selected_indices:
            if previous is not None and idx - previous > 1:
                output.append("...")
            output.append(sentences[idx])
            previous = idx

        return " ".join(output).strip()

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        size = min(len(a), len(b))
        if size == 0:
            return 0.0
        a = a[:size]
        b = b[:size]
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na == 0.0 or nb == 0.0:
            return 0.0
        raw = dot / (na * nb)
        return max(0.0, min(1.0, (raw + 1.0) / 2.0))
