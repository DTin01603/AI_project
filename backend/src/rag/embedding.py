"""Embedding models for RAG vector and hybrid search.

This module provides a provider-agnostic embedding interface with a practical
local fallback so tests and local development do not require heavyweight
ML dependencies.
"""

# pyright: reportMissingImports=false

from __future__ import annotations

import hashlib
import importlib
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheEntry:
    value: list[float]
    expires_at: float


class _TTLCache:
    """Simple in-memory TTL cache for embeddings."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> list[float] | None:
        now = time.time()
        entry = self._items.get(key)
        if entry is None:
            return None
        if entry.expires_at <= now:
            self._items.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: list[float]) -> None:
        if self.max_size <= 0:
            return

        if len(self._items) >= self.max_size:
            self._evict_oldest()

        self._items[key] = _CacheEntry(
            value=value,
            expires_at=time.time() + self.ttl_seconds,
        )

    def _evict_oldest(self) -> None:
        if not self._items:
            return
        oldest_key = min(self._items.items(), key=lambda kv: kv[1].expires_at)[0]
        self._items.pop(oldest_key, None)


class EmbeddingModel(ABC):
    """Abstract embedding model interface."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimensionality."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        return self.embed([query])[0]


class SentenceTransformerEmbedding(EmbeddingModel):
    """Sentence-transformers embedding with dependency-light fallback.

    If `sentence_transformers` is available, it will be used directly.
    Otherwise, a deterministic hash-based embedding is used for local tests.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
        batch_size: int = 32,
        token_limit: int = 512,
        cache_size: int = 1000,
        cache_ttl_seconds: int = 3600,
        normalize: bool = True,
    ) -> None:
        self.model_name = model_name
        self._dimension = dimension
        self.batch_size = max(1, batch_size)
        self.token_limit = max(1, token_limit)
        self.normalize = normalize
        self.cache = _TTLCache(max_size=cache_size, ttl_seconds=cache_ttl_seconds)

        self._backend: Any | None = None
        self._use_sentence_transformers = False

        try:
            module_name = "sentence" + "_transformers"
            module = importlib.import_module(module_name)
            SentenceTransformer = getattr(module, "SentenceTransformer")
            self._backend = SentenceTransformer(model_name)
            self._use_sentence_transformers = True
        except Exception:
            self._backend = None
            self._use_sentence_transformers = False

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for text in texts:
            cache_key = self._cache_key(text)
            cached = self.cache.get(cache_key)
            if cached is not None:
                vectors.append(cached)
                continue

            vector = self._embed_with_chunking(text)
            if self.normalize:
                vector = self._normalize(vector)
            self.cache.set(cache_key, vector)
            vectors.append(vector)

        return vectors

    def _embed_with_chunking(self, text: str) -> list[float]:
        tokens = text.split()
        if len(tokens) <= self.token_limit:
            return self._embed_single(text)

        # Average chunk embeddings when input exceeds token budget.
        chunks: list[str] = []
        for i in range(0, len(tokens), self.token_limit):
            chunks.append(" ".join(tokens[i : i + self.token_limit]))

        chunk_vectors = [self._embed_single(chunk) for chunk in chunks]

        avg = [0.0] * self.dimension
        for vector in chunk_vectors:
            for idx, value in enumerate(vector):
                avg[idx] += value

        count = float(len(chunk_vectors))
        return [v / count for v in avg]

    def _embed_single(self, text: str) -> list[float]:
        if self._use_sentence_transformers and self._backend is not None:
            encoded = self._backend.encode([text], normalize_embeddings=False)
            vector = [float(v) for v in encoded[0].tolist()]
            if len(vector) != self.dimension:
                vector = self._resize(vector)
            return vector

        return self._hash_embed(text)

    def _hash_embed(self, text: str) -> list[float]:
        # Deterministic fallback embedding for testability without external deps.
        dim = self.dimension
        values = [0.0] * dim
        seed = hashlib.sha256(text.encode("utf-8")).digest()

        for i in range(dim):
            block = hashlib.blake2b(seed + i.to_bytes(4, "little"), digest_size=8).digest()
            integer = int.from_bytes(block, "little", signed=False)
            values[i] = ((integer / (2**64 - 1)) * 2.0) - 1.0

        return values

    def _resize(self, vector: list[float]) -> list[float]:
        if len(vector) == self.dimension:
            return vector
        if len(vector) > self.dimension:
            return vector[: self.dimension]
        return vector + [0.0] * (self.dimension - len(vector))

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]

    @staticmethod
    def _cache_key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


class OpenAIEmbedding(EmbeddingModel):
    """Optional OpenAI embedding implementation.

    This class intentionally requires explicit dependency setup by callers.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "OpenAIEmbedding is optional and not configured in this project yet."
        )
