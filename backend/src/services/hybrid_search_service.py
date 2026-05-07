"""Hybrid search engine combining FTS and vector search."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from rag.embedding import EmbeddingModel
from rag.fts_engine import FTSEngine, SearchResult
from rag.query_expander import QueryExpander
from rag.vector_store import VectorStore


logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """Execute FTS and vector search in parallel and merge ranked results."""

    def __init__(
        self,
        fts_engine: FTSEngine,
        vector_store: VectorStore,
        embedding_model: EmbeddingModel,
        document_vector_store: VectorStore | None = None,
        query_expander: QueryExpander | None = None,
        fts_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> None:
        self.fts_engine = fts_engine
        self.vector_store = vector_store
        self.document_vector_store = document_vector_store
        self.embedding_model = embedding_model
        self.query_expander = query_expander
        self.fts_weight = fts_weight
        self.vector_weight = vector_weight

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
        enable_query_expansion: bool = False,
        query_expansion_count: int = 3,
    ) -> list[SearchResult]:
        if not query.strip():
            return []

        filters = filters or {}
        queries = [query]
        if enable_query_expansion and self.query_expander is not None:
            queries = self.query_expander.expand(query, max_alternatives=query_expansion_count)

        with ThreadPoolExecutor(max_workers=max(1, len(queries))) as pool:
            futures = {
                one_query: pool.submit(self._search_single_query, one_query, top_k, filters)
                for one_query in queries
            }

            merged_cross_query: dict[str, dict[str, Any]] = {}
            for one_query, future in futures.items():
                try:
                    rows = future.result()
                except Exception as exc:
                    logger.warning("Expanded query '%s' failed: %s", one_query, exc)
                    rows = []

                for row in rows:
                    bucket = merged_cross_query.get(row.id)
                    if bucket is None:
                        merged_cross_query[row.id] = {
                            "row": row,
                            "matched_queries": [one_query],
                        }
                    else:
                        if one_query not in bucket["matched_queries"]:
                            bucket["matched_queries"].append(one_query)
                        if row.score > bucket["row"].score:
                            bucket["row"] = row

        results: list[SearchResult] = []
        for payload in merged_cross_query.values():
            row: SearchResult = payload["row"]
            matched_queries: list[str] = payload["matched_queries"]
            results.append(
                SearchResult(
                    id=row.id,
                    content=row.content,
                    score=row.score,
                    metadata={
                        **row.metadata,
                        "matched_queries": matched_queries,
                        "query_match_count": len(matched_queries),
                    },
                    source_type=row.source_type,
                )
            )

        results = [row for row in results if row.score >= min_score]
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    def _search_single_query(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> list[SearchResult]:
        source_types = self._extract_source_types(filters)
        query_fts = self._should_query_fts(source_types)
        query_conversation_vectors = self._should_query_conversation_vectors(source_types)
        query_document_vectors = self._should_query_document_vectors(source_types)

        futures: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            if query_fts:
                fts_filters = self._filters_without_source_constraints(filters)
                futures["fts"] = pool.submit(
                    self.fts_engine.search,
                    query,
                    top_k,
                    0.0,
                    fts_filters,
                )

            if query_conversation_vectors:
                conv_filters = dict(filters)
                conv_filters["source_type"] = "conversation"
                futures["conversation_vector"] = pool.submit(
                    self._vector_search,
                    query,
                    top_k,
                    conv_filters,
                    self.vector_store,
                )

            if query_document_vectors and self.document_vector_store is not None:
                doc_filters = dict(filters)
                if "source_type" not in doc_filters and "source_types" not in doc_filters:
                    doc_filters["source_types"] = ["document", "code_file"]
                futures["document_vector"] = pool.submit(
                    self._vector_search,
                    query,
                    top_k,
                    doc_filters,
                    self.document_vector_store,
                )

            source_errors: dict[str, Exception] = {}
            source_results: dict[str, list[Any]] = {}
            for source_name, future in futures.items():
                try:
                    source_results[source_name] = future.result()
                except Exception as exc:
                    source_errors[source_name] = exc
                    source_results[source_name] = []

        if source_errors and len(source_errors) == len(futures):
            error_parts = ", ".join(f"{k}={v}" for k, v in source_errors.items())
            raise RuntimeError(f"All retrieval sources failed: {error_parts}")

        for source_name, error in source_errors.items():
            logger.warning("Retrieval source '%s' failed: %s", source_name, error)

        fts_results = source_results.get("fts", [])
        vector_results: list[dict[str, Any]] = []
        vector_results.extend(source_results.get("conversation_vector", []))
        vector_results.extend(source_results.get("document_vector", []))

        if not vector_results:
            merged = self._fts_only(fts_results)
        elif not fts_results:
            merged = self._vector_only(vector_results)
        else:
            merged = self._merge_results(fts_results, vector_results)
        return merged[:top_k]

    def _vector_search(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        vector_store: VectorStore,
    ) -> list[dict[str, Any]]:
        query_embedding = self.embedding_model.embed_query(query)
        return vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters,
        )

    @staticmethod
    def _extract_source_types(filters: dict[str, Any]) -> set[str]:
        source_type = filters.get("source_type")
        source_types = filters.get("source_types")

        normalized: set[str] = set()
        if isinstance(source_type, str) and source_type:
            normalized.add(source_type)

        if isinstance(source_types, list):
            for item in source_types:
                if isinstance(item, str) and item:
                    normalized.add(item)

        return normalized

    @staticmethod
    def _filters_without_source_constraints(filters: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(filters)
        cleaned.pop("source_type", None)
        cleaned.pop("source_types", None)
        return cleaned

    @staticmethod
    def _should_query_fts(source_types: set[str]) -> bool:
        if not source_types:
            return True
        return "conversation" in source_types

    @staticmethod
    def _should_query_conversation_vectors(source_types: set[str]) -> bool:
        if not source_types:
            return True
        return "conversation" in source_types

    @staticmethod
    def _should_query_document_vectors(source_types: set[str]) -> bool:
        if not source_types:
            return True
        return bool(source_types.intersection({"document", "code_file"}))

    @staticmethod
    def _fts_only(fts_results: list[SearchResult]) -> list[SearchResult]:
        return [
            SearchResult(
                id=r.id,
                content=r.content,
                score=max(0.0, min(1.0, r.score)),
                metadata=r.metadata,
                source_type=r.source_type,
            )
            for r in fts_results
        ]

    @staticmethod
    def _vector_only(vector_results: list[dict[str, Any]]) -> list[SearchResult]:
        rows: list[SearchResult] = []
        for r in vector_results:
            rows.append(
                SearchResult(
                    id=str(r["id"]),
                    content=str(r.get("text", "")),
                    score=max(0.0, min(1.0, float(r.get("score", 0.0)))),
                    metadata=dict(r.get("metadata", {})),
                    source_type=str(r.get("metadata", {}).get("source_type", "conversation")),
                )
            )
        return rows

    def _merge_results(
        self,
        fts_results: list[SearchResult],
        vector_results: list[dict[str, Any]],
    ) -> list[SearchResult]:
        merged: dict[str, dict[str, Any]] = {}

        for row in fts_results:
            merged[row.id] = {
                "id": row.id,
                "content": row.content,
                "metadata": dict(row.metadata),
                "source_type": row.source_type,
                "fts_score": max(0.0, min(1.0, row.score)),
                "vector_score": 0.0,
            }

        for row in vector_results:
            doc_id = str(row["id"])
            bucket = merged.get(doc_id)
            if bucket is None:
                merged[doc_id] = {
                    "id": doc_id,
                    "content": str(row.get("text", "")),
                    "metadata": dict(row.get("metadata", {})),
                    "source_type": str(row.get("metadata", {}).get("source_type", "conversation")),
                    "fts_score": 0.0,
                    "vector_score": max(0.0, min(1.0, float(row.get("score", 0.0)))),
                }
            else:
                bucket["vector_score"] = max(
                    bucket["vector_score"],
                    max(0.0, min(1.0, float(row.get("score", 0.0)))),
                )
                if not bucket["content"] and row.get("text"):
                    bucket["content"] = str(row["text"])

        rows: list[SearchResult] = []
        for item in merged.values():
            score = (self.fts_weight * item["fts_score"]) + (
                self.vector_weight * item["vector_score"]
            )
            rows.append(
                SearchResult(
                    id=item["id"],
                    content=item["content"],
                    score=max(0.0, min(1.0, score)),
                    metadata=item["metadata"],
                    source_type=item["source_type"],
                )
            )

        rows.sort(key=lambda x: x.score, reverse=True)
        return rows
