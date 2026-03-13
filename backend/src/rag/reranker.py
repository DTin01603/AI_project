"""Result reranker for hybrid retrieval pipelines."""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Any

from rag.embedding import EmbeddingModel
from rag.fts_engine import SearchResult

logger = logging.getLogger(__name__)


class ReRanker:
    """Re-rank retrieved documents using Cross-Encoder with cosine fallback.

    Uses a cross-encoder model for accurate semantic re-ranking. Falls back to
    cosine similarity if the cross-encoder fails to load or encounters errors.
    
    Cross-encoders process query-document pairs jointly, providing better
    relevance scores than bi-encoder approaches at the cost of higher latency.
    """

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        cache_size: int = 1000,
    ) -> None:
        self.embedding_model = embedding_model
        self.model_name = model_name
        self.cache_size = max(0, cache_size)
        self._score_cache: dict[str, float] = {}
        self._cross_encoder = self._load_cross_encoder()

    def rerank(self, query: str, documents: list[SearchResult], top_n: int | None = None) -> list[SearchResult]:
        if not documents:
            return []

        rescored: list[tuple[int, SearchResult, float]] = []
        for idx, doc in enumerate(documents):
            score = self._score_pair(query, doc.content)
            rescored.append((idx, doc, score))

        # Python sort is stable; index tie-break makes expectation explicit.
        rescored.sort(key=lambda item: (item[2], -item[0]), reverse=True)

        ranked = [
            SearchResult(
                id=item[1].id,
                content=item[1].content,
                score=max(0.0, min(1.0, item[2])),
                metadata=item[1].metadata,
                source_type=item[1].source_type,
            )
            for item in rescored
        ]

        if top_n is None:
            return ranked
        return ranked[: max(1, top_n)]

    def _load_cross_encoder(self) -> Any | None:
        """Load cross-encoder model with graceful fallback.
        
        Returns:
            CrossEncoder instance or None if loading fails
        """
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            model = CrossEncoder(self.model_name, max_length=512)
            logger.info("Cross-encoder loaded successfully")
            return model
        except ImportError:
            logger.warning(
                "sentence-transformers not available, falling back to cosine similarity"
            )
            return None
        except Exception as e:
            logger.warning(
                f"Failed to load cross-encoder {self.model_name}: {e}. "
                "Falling back to cosine similarity"
            )
            return None

    def _score_pair(self, query: str, content: str) -> float:
        """Score a query-document pair using cross-encoder or cosine fallback.
        
        Args:
            query: Search query
            content: Document content
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        cache_key = self._cache_key(query, content)
        cached = self._score_cache.get(cache_key)
        if cached is not None:
            return cached

        # Use cross-encoder if available, otherwise fall back to cosine
        if self._cross_encoder is not None:
            try:
                score = self._cross_encoder_score(query, content)
            except Exception as e:
                logger.warning(f"Cross-encoder scoring failed: {e}, using cosine fallback")
                score = self._cosine_fallback_score(query, content)
        else:
            score = self._cosine_fallback_score(query, content)

        # Cache management
        if self.cache_size > 0:
            if len(self._score_cache) >= self.cache_size:
                oldest_key = next(iter(self._score_cache))
                self._score_cache.pop(oldest_key, None)
            self._score_cache[cache_key] = score

        return score

    def _cross_encoder_score(self, query: str, content: str) -> float:
        """Score using cross-encoder model.
        
        Args:
            query: Search query
            content: Document content
            
        Returns:
            Normalized score between 0.0 and 1.0
        """
        # Cross-encoder expects list of [query, document] pairs
        scores = self._cross_encoder.predict([[query, content]])
        
        # CrossEncoder returns raw logits, normalize to [0, 1]
        # Using sigmoid for MS MARCO models
        raw_score = float(scores[0])
        normalized = 1.0 / (1.0 + math.exp(-raw_score))
        
        return max(0.0, min(1.0, normalized))

    def _cosine_fallback_score(self, query: str, content: str) -> float:
        q_vec = self.embedding_model.embed_query(query)
        d_vec = self.embedding_model.embed_query(content)

        size = min(len(q_vec), len(d_vec))
        q_vec = q_vec[:size]
        d_vec = d_vec[:size]

        dot = sum(x * y for x, y in zip(q_vec, d_vec))
        nq = math.sqrt(sum(x * x for x in q_vec))
        nd = math.sqrt(sum(y * y for y in d_vec))
        if nq == 0.0 or nd == 0.0:
            return 0.0

        cosine = dot / (nq * nd)
        return max(0.0, min(1.0, (cosine + 1.0) / 2.0))

    @staticmethod
    def _cache_key(query: str, content: str) -> str:
        return hashlib.sha256(f"{query}\n{content}".encode("utf-8")).hexdigest()
