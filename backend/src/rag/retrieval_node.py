"""Retrieval Node for LangGraph integration.

This module provides the RetrievalNode class that integrates RAG retrieval
into the LangGraph workflow, extracting queries from agent state and adding
retrieved documents back to the state.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage
from typing_extensions import NotRequired, TypedDict

from rag.embedding import EmbeddingModel, SentenceTransformerEmbedding
from rag.config import RAGConfig
from rag.contextual_compressor import ContextualCompressor
from rag.citation_tracker import CitationTracker
from rag.fts_engine import FTSEngine, SearchResult
from rag.hybrid_search import HybridSearchEngine
from rag.metrics import RAGMetrics, get_metrics
from rag.multi_query_retriever import MultiQueryRetriever
from rag.query_expander import QueryExpander
from rag.reranker import ReRanker
from rag.vector_store import ChromaVectorStore, VectorStore, build_conversation_collection_name

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


@dataclass
class RetrievedDocument:
    """Document retrieved by the retrieval node."""

    id: str
    content: str
    score: float
    source_type: str
    metadata: dict[str, Any]


class RetrievalMetadata(TypedDict):
    """Metadata about the retrieval operation."""

    query: str
    method: str
    result_count: int
    execution_time_ms: float
    top_score: NotRequired[float]


class RetrievalNode:
    """LangGraph node for executing retrieval operations.
    
    Integrates into the LangGraph workflow to provide RAG capabilities:
    - Extracts query from state.messages
    - Executes search using configured method (FTS, vector, or hybrid)
    - Adds retrieved documents to state for downstream nodes
    - Logs retrieval operations with timing and result metrics
    
    Supports configurable search parameters:
    - search_method: "fts", "vector", or "hybrid" (Phase 1: only "fts")
    - top_k: Number of results to return (default: 5)
    - min_score: Minimum relevance threshold (default: 0.0)
    """

    def __init__(
        self,
        fts_engine: FTSEngine,
        config: RAGConfig | None = None,
        metrics: RAGMetrics | None = None,
        embedding_model: EmbeddingModel | None = None,
        vector_store: VectorStore | None = None,
        document_vector_store: VectorStore | None = None,
        hybrid_search: HybridSearchEngine | None = None,
        reranker: ReRanker | None = None,
    ):
        """Initialize retrieval node with search backend.
        
        Args:
            fts_engine: Full-text search engine for keyword search
            config: RAG configuration (uses defaults if not provided)
            metrics: Metrics tracker (uses global instance if not provided)
        """
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
        self.citation_tracker = (
            CitationTracker(db_path=self.fts_engine.db_path)
            if self.config.enable_citations
            else None
        )
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

        # Retain this attribute for backward compatibility with Phase 1 tests.
        self.vector_search = self.vector_store

        self._bootstrap_vector_index()

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute retrieval based on current query in state.
        
        Extracts the query from the last message in state.messages,
        executes the configured search method, and adds retrieved
        documents to the state.
        
        Args:
            state: AgentState dictionary with messages field
            
        Returns:
            Updated state with retrieved_documents and retrieval_metadata
        """
        import time
        
        start_time = time.time()
        error_msg = None
        
        # Extract query from last message
        query = self._extract_query(state)
        
        if not query:
            logger.warning("No query found in state messages")
            
            # Record metrics for empty query
            self.metrics.record_retrieval(
                query="",
                method="none",
                result_count=0,
                execution_time_ms=0.0,
                error="No query found in state",
            )
            
            return {
                "retrieved_documents": [],
                "retrieval_metadata": {
                    "query": "",
                    "method": "none",
                    "result_count": 0,
                    "execution_time_ms": 0.0,
                },
            }
        
        # Execute retrieval with default configuration
        method = self.config.default_search_method
        top_k = self.config.default_top_k
        min_score = self.config.min_relevance_score
        filters = state.get("retrieval_filters") if isinstance(state.get("retrieval_filters"), dict) else None
        
        try:
            results = self.retrieve(
                query=query,
                method=method,
                top_k=top_k,
                min_score=min_score,
                filters=filters,
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Retrieval failed: {error_msg}", exc_info=True)
            results = []
        
        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Build metadata
        metadata: RetrievalMetadata = {
            "query": query,
            "method": method,
            "result_count": len(results),
            "execution_time_ms": execution_time_ms,
        }
        
        top_score = None
        if results:
            top_score = results[0].score
            metadata["top_score"] = top_score
        
        # Record metrics
        self.metrics.record_retrieval(
            query=query,
            method=method,
            result_count=len(results),
            execution_time_ms=execution_time_ms,
            top_score=top_score,
            error=error_msg,
        )
        
        # Enhanced logging with all required information
        truncated_query = query[:50] + "..." if len(query) > 50 else query
        log_msg = (
            f"Retrieval completed: query='{truncated_query}', "
            f"method={method}, results={len(results)}, "
            f"time={execution_time_ms:.2f}ms"
        )
        
        if top_score is not None:
            log_msg += f", top_score={top_score:.3f}"
        
        if error_msg:
            log_msg += f", error={error_msg}"
        
        logger.info(log_msg)
        
        return {
            "retrieved_documents": results,
            "retrieval_metadata": metadata,
        }

    def _extract_query(self, state: dict[str, Any]) -> str:
        """Extract query from the last message in state.
        
        Args:
            state: AgentState dictionary
            
        Returns:
            Query string extracted from last message, or empty string if not found
        """
        messages = state.get("messages", [])
        
        if not messages:
            return ""
        
        # Get the last message
        last_message = messages[-1]
        
        # Extract content based on message type
        if isinstance(last_message, (HumanMessage, AIMessage)):
            return str(last_message.content)
        elif isinstance(last_message, dict):
            return str(last_message.get("content", ""))
        else:
            # Fallback: try to convert to string
            return str(last_message)

    def retrieve(
        self,
        query: str,
        method: Literal["fts", "vector", "hybrid"] = "fts",
        top_k: int = 5,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Execute retrieval with specified method and parameters.
        
        Args:
            query: Search query string
            method: Search method ("fts", "vector", or "hybrid")
            top_k: Maximum number of results to return
            min_score: Minimum relevance score threshold (0-1 range)
            
        Returns:
            List of RetrievedDocument ordered by descending relevance score
            
        Raises:
            ValueError: If method is not supported in current phase
        """
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

            if self.config.enable_citations and self.citation_tracker is not None and docs:
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

    def _retrieve_fts(
        self,
        query: str,
        top_k: int,
        min_score: float,
        filters: dict[str, Any] | None,
    ) -> list[RetrievedDocument]:
        """Execute FTS retrieval.
        
        Args:
            query: Search query string
            top_k: Maximum number of results
            min_score: Minimum score threshold
            
        Returns:
            List of RetrievedDocument from FTS search
        """
        # Execute FTS search
        fts_results = self.fts_engine.search(
            query=query,
            limit=top_k,
            min_score=min_score,
            filters=self._normalize_filters(filters, fts_only=True),
        )
        
        # Convert SearchResult to RetrievedDocument
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
        cited_docs: list[RetrievedDocument] = []
        for doc in docs:
            title = str(doc.metadata.get("title") or doc.metadata.get("file_name") or doc.id)
            author = doc.metadata.get("author")
            created_at = doc.metadata.get("created_at")

            citation = self.citation_tracker.create_citation(
                document_id=doc.id,
                chunk_id=str(doc.metadata.get("chunk_id")) if doc.metadata.get("chunk_id") else None,
                source_type=doc.source_type,
                title=title,
                author=str(author) if author else None,
                created_at=str(created_at) if created_at else None,
                metadata=doc.metadata,
            )
            self.citation_tracker.track_usage(citation.citation_id, query, used_in_response=True)

            metadata = {
                **doc.metadata,
                "citation_id": citation.citation_id,
                "citation_apa": self.citation_tracker.format_citation(citation, style="APA"),
                "citation_mla": self.citation_tracker.format_citation(citation, style="MLA"),
                "citation_chicago": self.citation_tracker.format_citation(citation, style="Chicago"),
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
        """Load existing messages into vector store if collection is empty."""
        db_path = self.fts_engine.db_path
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT id, content, conversation_id, role, created_at
                FROM messages
                ORDER BY created_at ASC
                """
            ).fetchall()
        finally:
            conn.close()

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
