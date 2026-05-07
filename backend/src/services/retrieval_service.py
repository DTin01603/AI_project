"""Retrieval orchestration service.

Owns the full retrieval pipeline: FTS / vector / hybrid / multi-query →
optional rerank → optional contextual compression → optional citation
attachment. Knows nothing about LangGraph state. The thin LangGraph
adapter lives in `agent/nodes/retrieval_node.py`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from models.search import RetrievedDocument, SearchResult
from rag.config import RAGConfig
from rag.contextual_compressor import ContextualCompressor
from rag.embedding import EmbeddingModel, SentenceTransformerEmbedding
from rag.fts_engine import FTSEngine
from rag.metrics import RAGMetrics, get_metrics
from rag.query_expander import QueryExpander
from rag.reranker import ReRanker
from rag.vector_store import ChromaVectorStore, VectorStore, build_conversation_collection_name
from repositories.citation_repo import CitationRepository
from services.citation_service import CitationService
from services.hybrid_search_service import HybridSearchEngine
from services.multi_query_service import MultiQueryRetriever

try:
    from langsmith import traceable
except Exception:  # pragma: no cover - optional dependency at runtime
    traceable = None


logger = logging.getLogger(__name__)


def _is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _langsmith_manual_tracing_enabled() -> bool:
    if traceable is None:
        return False
    if not os.getenv("LANGSMITH_API_KEY", "").strip():
        return False
    return _is_truthy_env("LANGSMITH_TRACING") or _is_truthy_env("LANGCHAIN_TRACING_V2")


class RetrievalService:
    """Hybrid retrieval pipeline: search → rerank → compress → citations."""

    def __init__(
        self,
        *,
        fts_engine: FTSEngine,
        config: RAGConfig | None = None,
        metrics: RAGMetrics | None = None,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
        document_vector_store: VectorStore | None = None,
        hybrid_search: HybridSearchEngine | None = None,
        reranker: ReRanker | None = None,
        connection_factory: SQLiteConnectionFactory | None = None,
    ) -> None:
        self.fts_engine = fts_engine
        self.config = config or RAGConfig()
        self.metrics = metrics or get_metrics()
        self.embedding_model = embedding_model or SentenceTransformerEmbedding(
            model_name=self.config.embedding_model,
            dimension=self.config.embedding_dimension,
            batch_size=self.config.batch_size,
            cache_size=self.config.cache_size,
        )

        conversation_collection = build_conversation_collection_name(self.fts_engine.db_path)
        self.vector_store = vector_store or ChromaVectorStore(
            persist_directory=self.config.vector_store_path,
            collection_name=conversation_collection,
        )
        self.document_vector_store = document_vector_store or ChromaVectorStore(
            persist_directory=self.config.vector_store_path,
            collection_name="indexed_documents",
        )
        self.query_expander = (
            QueryExpander(
                max_expansions=self.config.query_expansion_count,
                timeout_ms=200,
                cache_size=self.config.cache_size,
            )
            if self.config.enable_query_expansion
            else None
        )
        self.contextual_compressor = (
            ContextualCompressor(embedding_model=self.embedding_model)
            if self.config.enable_compression
            else None
        )
        # When citations are enabled, build a CitationService over the same
        # DB. The injected `connection_factory` is preferred so the service
        # shares the AppContainer's factory; otherwise fall back to a fresh
        # one pointing at fts_engine's path (matches the legacy shim).
        if self.config.enable_citations:
            citation_factory = connection_factory or SQLiteConnectionFactory(self.fts_engine.db_path)
            run_migrations(citation_factory)
            self.citation_service: CitationService | None = CitationService(
                CitationRepository(citation_factory), citation_factory
            )
        else:
            self.citation_service = None
        self.hybrid_search = hybrid_search or HybridSearchEngine(
            fts_engine=self.fts_engine,
            vector_store=self.vector_store,
            embedding_model=self.embedding_model,
            document_vector_store=self.document_vector_store,
            query_expander=self.query_expander,
            fts_weight=self.config.fts_weight,
            vector_weight=self.config.vector_weight,
        )
        self.multi_query_retriever = (
            MultiQueryRetriever(
                search_fn=self._hybrid_search_fn,
                max_sub_queries=4,
            )
            if self.config.enable_multi_query
            else None
        )
        self.reranker = reranker or ReRanker(
            embedding_model=self.embedding_model,
            model_name=self.config.reranker_model,
            cache_size=self.config.cache_size,
        )

        # Connection factory used only by _bootstrap_vector_index. Defaults
        # to a fresh factory pointing at the same DB as fts_engine when one
        # is not injected — avoids reaching into FTSEngine privates.
        self._factory = connection_factory or SQLiteConnectionFactory(self.fts_engine.db_path)

        self._bootstrap_vector_index()

    # ------------------------------------------------------------------ retrieve

    def retrieve(
        self,
        query: str,
        method: Literal["fts", "vector", "hybrid"] = "fts",
        top_k: int = 5,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        def _execute_retrieval(
            *,
            traced_query: str,
            traced_method: Literal["fts", "vector", "hybrid"],
            traced_top_k: int,
            traced_min_score: float,
            traced_filters: dict[str, Any] | None,
        ) -> list[RetrievedDocument]:
            if not traced_query or not traced_query.strip():
                return []

            if traced_method == "fts":
                docs = self._retrieve_fts(traced_query, traced_top_k, traced_min_score, traced_filters)
            elif traced_method == "vector":
                docs = self._retrieve_vector(traced_query, traced_top_k, traced_min_score, traced_filters)
            elif traced_method == "hybrid":
                if self.config.enable_multi_query:
                    docs = self._retrieve_multi_query(traced_query, traced_top_k, traced_min_score, traced_filters)
                else:
                    docs = self._retrieve_hybrid(traced_query, traced_top_k, traced_min_score, traced_filters)
            else:
                raise ValueError(f"Unknown search method: {traced_method}")

            if self.config.enable_reranking and docs:
                rerank_limit = min(len(docs), self.config.rerank_top_n)
                head = self.reranker.rerank(traced_query, docs[:rerank_limit], top_n=rerank_limit)
                docs = head + docs[rerank_limit:]

            if self.config.enable_compression and self.contextual_compressor is not None and docs:
                docs = self._compress_documents(traced_query, docs)

            if self.config.enable_citations and self.citation_service is not None and docs:
                docs = self._attach_citations(traced_query, docs)

            return docs

        if _langsmith_manual_tracing_enabled():
            traced_execute = traceable(name="rag.retrieve", run_type="retriever")(_execute_retrieval)
            return traced_execute(
                traced_query=query,
                traced_method=method,
                traced_top_k=top_k,
                traced_min_score=min_score,
                traced_filters=filters,
            )

        return _execute_retrieval(
            traced_query=query,
            traced_method=method,
            traced_top_k=top_k,
            traced_min_score=min_score,
            traced_filters=filters,
        )

    # ------------------------------------------------------------------ retrieval methods

    def _retrieve_fts(
        self,
        query: str,
        top_k: int,
        min_score: float,
        filters: dict[str, Any] | None,
    ) -> list[RetrievedDocument]:
        fts_results = self.fts_engine.search(
            query=query,
            limit=top_k,
            min_score=min_score,
            filters=self._normalize_filters(filters, fts_only=True),
        )
        return [
            RetrievedDocument(
                id=result.id,
                content=result.content,
                score=result.score,
                source_type=result.source_type,
                metadata=result.metadata,
            )
            for result in fts_results
        ]

    def _retrieve_vector(
        self,
        query: str,
        top_k: int,
        min_score: float,
        filters: dict[str, Any] | None,
    ) -> list[RetrievedDocument]:
        query_embedding = self.embedding_model.embed_query(query)
        normalized = self._normalize_filters(filters)

        source_types = self._extract_source_types(normalized)
        query_conversation = not source_types or "conversation" in source_types
        query_documents = bool(source_types.intersection({"document", "code_file"})) if source_types else True

        vector_results: list[dict[str, Any]] = []

        if query_conversation:
            conv_filters = dict(normalized)
            conv_filters["source_type"] = "conversation"
            vector_results.extend(
                self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=top_k,
                    filters=conv_filters,
                )
            )

        if query_documents:
            doc_filters = dict(normalized)
            if "source_type" not in doc_filters and "source_types" not in doc_filters:
                doc_filters["source_types"] = ["document", "code_file"]
            vector_results.extend(
                self.document_vector_store.search(
                    query_embedding=query_embedding,
                    top_k=top_k,
                    filters=doc_filters,
                )
            )

        vector_results.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        vector_results = vector_results[:top_k]

        docs: list[RetrievedDocument] = []
        for result in vector_results:
            score = float(result.get("score", 0.0))
            if score < min_score:
                continue
            metadata = dict(result.get("metadata", {}))
            docs.append(
                RetrievedDocument(
                    id=str(result["id"]),
                    content=str(result.get("text", "")),
                    score=score,
                    source_type=str(metadata.get("source_type", "conversation")),
                    metadata=metadata,
                )
            )

        return docs

    def _retrieve_hybrid(
        self,
        query: str,
        top_k: int,
        min_score: float,
        filters: dict[str, Any] | None,
    ) -> list[RetrievedDocument]:
        hybrid_results = self.hybrid_search.search(
            query=query,
            top_k=top_k,
            min_score=min_score,
            filters=self._normalize_filters(filters),
            enable_query_expansion=self.config.enable_query_expansion,
            query_expansion_count=self.config.query_expansion_count,
        )
        return [
            RetrievedDocument(
                id=result.id,
                content=result.content,
                score=result.score,
                source_type=result.source_type,
                metadata=result.metadata,
            )
            for result in hybrid_results
        ]

    def _retrieve_multi_query(
        self,
        query: str,
        top_k: int,
        min_score: float,
        filters: dict[str, Any] | None,
    ) -> list[RetrievedDocument]:
        if self.multi_query_retriever is None:
            return self._retrieve_hybrid(query, top_k, min_score, filters)

        results = self.multi_query_retriever.retrieve(
            query=query,
            top_k=top_k,
            min_score=min_score,
            filters=self._normalize_filters(filters),
        )
        return [
            RetrievedDocument(
                id=item.result.id,
                content=item.result.content,
                score=item.result.score,
                source_type=item.result.source_type,
                metadata=item.result.metadata,
            )
            for item in results
        ]

    # ------------------------------------------------------------------ post-processing

    def _compress_documents(self, query: str, docs: list[RetrievedDocument]) -> list[RetrievedDocument]:
        compressed_docs: list[RetrievedDocument] = []
        for doc in docs:
            compressed = self.contextual_compressor.compress(
                query=query,
                document_text=doc.content,
                relevance_score=doc.score,
                min_ratio=self.config.compression_min_ratio,
                max_ratio=self.config.compression_max_ratio,
            )
            metadata = {
                **doc.metadata,
                "compression": {
                    "ratio": compressed.compression_ratio,
                    "selected_sentences": compressed.selected_sentences,
                    "total_sentences": compressed.total_sentences,
                },
            }
            compressed_docs.append(
                RetrievedDocument(
                    id=doc.id,
                    content=compressed.text,
                    score=doc.score,
                    source_type=doc.source_type,
                    metadata=metadata,
                )
            )
        return compressed_docs

    def _attach_citations(self, query: str, docs: list[RetrievedDocument]) -> list[RetrievedDocument]:
        assert self.citation_service is not None  # guarded by caller
        cited_docs: list[RetrievedDocument] = []
        for doc in docs:
            title = str(doc.metadata.get("title") or doc.metadata.get("file_name") or doc.id)
            author = doc.metadata.get("author")
            created_at = doc.metadata.get("created_at")

            citation = self.citation_service.create_citation(
                document_id=doc.id,
                chunk_id=str(doc.metadata.get("chunk_id")) if doc.metadata.get("chunk_id") else None,
                source_type=doc.source_type,
                title=title,
                author=str(author) if author else None,
                created_at=str(created_at) if created_at else None,
                metadata=doc.metadata,
            )
            self.citation_service.track_usage(citation.citation_id, query, used_in_response=True)

            metadata = {
                **doc.metadata,
                "citation_id": citation.citation_id,
                "citation_apa": citation.format("APA"),
                "citation_mla": citation.format("MLA"),
                "citation_chicago": citation.format("Chicago"),
            }
            cited_docs.append(
                RetrievedDocument(
                    id=doc.id,
                    content=doc.content,
                    score=doc.score,
                    source_type=doc.source_type,
                    metadata=metadata,
                )
            )
        return cited_docs

    # ------------------------------------------------------------------ helpers

    def _hybrid_search_fn(
        self,
        query: str,
        top_k: int,
        min_score: float,
        filters: dict[str, Any] | None,
    ) -> list[SearchResult]:
        normalized_filters = self._normalize_filters(filters)
        return self.hybrid_search.search(
            query=query,
            top_k=top_k,
            min_score=min_score,
            filters=normalized_filters,
            enable_query_expansion=self.config.enable_query_expansion and self.query_expander is not None,
            query_expansion_count=self.config.query_expansion_count,
        )

    @staticmethod
    def _normalize_filters(filters: dict[str, Any] | None, fts_only: bool = False) -> dict[str, Any]:
        normalized = dict(filters or {})
        if fts_only:
            source_type = normalized.get("source_type")
            source_types = normalized.get("source_types")

            if source_type and source_type != "conversation":
                return {"conversation_id": "__none__"}

            if isinstance(source_types, list) and source_types and "conversation" not in source_types:
                return {"conversation_id": "__none__"}

            normalized.pop("source_type", None)
            normalized.pop("source_types", None)

        return normalized

    @staticmethod
    def _extract_source_types(filters: dict[str, Any]) -> set[str]:
        source_types: set[str] = set()
        source_type = filters.get("source_type")
        if isinstance(source_type, str) and source_type:
            source_types.add(source_type)
        list_types = filters.get("source_types")
        if isinstance(list_types, list):
            source_types.update(str(item) for item in list_types if isinstance(item, str) and item)
        return source_types

    def _bootstrap_vector_index(self) -> None:
        """Backfill the conversation vector collection from `messages` rows."""
        with self._factory.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, content, conversation_id, role, created_at
                FROM messages
                ORDER BY created_at ASC
                """
            ).fetchall()

        if not rows:
            return

        sample_embedding = self.embedding_model.embed_query("__bootstrap_probe__")
        probe_results = self.vector_store.search(sample_embedding, top_k=1)
        if probe_results:
            return

        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for row in rows:
            ids.append(str(row["id"]))
            texts.append(str(row["content"]))
            metadatas.append(
                {
                    "conversation_id": str(row["conversation_id"]),
                    "role": str(row["role"]),
                    "created_at": str(row["created_at"]),
                    "source_type": "conversation",
                }
            )

        embeddings = self.embedding_model.embed(texts)
        self.vector_store.add(ids=ids, embeddings=embeddings, texts=texts, metadatas=metadatas)
        self.vector_store.persist()


__all__ = ["RetrievalService"]
