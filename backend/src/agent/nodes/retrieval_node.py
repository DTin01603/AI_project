"""LangGraph adapter for the retrieval pipeline.

The actual orchestration lives in `services.retrieval_service.RetrievalService`.
This module is a thin shim that:

1. Extracts the query from `state.messages`.
2. Calls `service.retrieve(...)`.
3. Records metrics + builds a state update with `retrieved_documents` and
   `retrieval_metadata`.

Construct via `RetrievalNode(service=...)`. The legacy ``RetrievalNode(fts_engine=..., config=...)``
signature has been removed — `AppContainer` now builds a `RetrievalService`
explicitly and passes it in.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage
from typing_extensions import NotRequired, TypedDict

from models.search import RetrievedDocument
from rag.metrics import RAGMetrics, get_metrics
from services.retrieval_service import RetrievalService


logger = logging.getLogger(__name__)


class RetrievalMetadata(TypedDict):
    """Shape of the `retrieval_metadata` state update emitted by the node."""

    query: str
    method: str
    result_count: int
    execution_time_ms: float
    top_score: NotRequired[float]


class RetrievalNode:
    """Adapter: AgentState → RetrievalService.retrieve → AgentState update."""

    def __init__(
        self,
        service: RetrievalService,
        *,
        metrics: RAGMetrics | None = None,
    ) -> None:
        self.service = service
        self.config = service.config
        self.metrics = metrics or get_metrics()

    # ------------------------------------------------------------------ proxies

    @property
    def fts_engine(self):
        # Kept so callers that historically reached for `node.fts_engine` (e.g.
        # the search router's health check) keep working without an explicit
        # service handle.
        return self.service.fts_engine

    def retrieve(
        self,
        query: str,
        method: Literal["fts", "vector", "hybrid"] = "fts",
        top_k: int = 5,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        return self.service.retrieve(
            query=query,
            method=method,
            top_k=top_k,
            min_score=min_score,
            filters=filters,
        )

    # ------------------------------------------------------------------ node entry

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        start_time = time.time()
        error_msg: str | None = None

        query = self._extract_query(state)
        if not query:
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

        method = self.config.default_search_method
        top_k = self.config.default_top_k
        min_score = self.config.min_relevance_score
        filters = state.get("retrieval_filters") if isinstance(state.get("retrieval_filters"), dict) else None

        try:
            results = self.service.retrieve(
                query=query,
                method=method,
                top_k=top_k,
                min_score=min_score,
                filters=filters,
            )
        except Exception as exc:
            error_msg = str(exc)
            logger.error("Retrieval failed: %s", error_msg, exc_info=True)
            results = []

        execution_time_ms = (time.time() - start_time) * 1000
        metadata: RetrievalMetadata = {
            "query": query,
            "method": method,
            "result_count": len(results),
            "execution_time_ms": execution_time_ms,
        }
        top_score: float | None = None
        if results:
            top_score = results[0].score
            metadata["top_score"] = top_score

        self.metrics.record_retrieval(
            query=query,
            method=method,
            result_count=len(results),
            execution_time_ms=execution_time_ms,
            top_score=top_score,
            error=error_msg,
        )

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

    @staticmethod
    def _extract_query(state: dict[str, Any]) -> str:
        messages = state.get("messages", [])
        if not messages:
            return ""
        last_message = messages[-1]
        if isinstance(last_message, (HumanMessage, AIMessage)):
            return str(last_message.content)
        if isinstance(last_message, dict):
            return str(last_message.get("content", ""))
        return str(last_message)


__all__ = ["RetrievalNode", "RetrievalMetadata"]
