"""Metrics tracking for RAG retrieval operations.

This module provides the RAGMetrics class for tracking and exporting metrics
related to retrieval operations, including latency, result counts, cache hits,
and error rates.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class RetrievalMetrics:
    """Metrics for a single retrieval operation."""

    query: str
    method: str
    result_count: int
    execution_time_ms: float
    top_score: float | None = None
    timestamp: float = field(default_factory=time.time)
    error: str | None = None


@dataclass
class MetricsSummary:
    """Summary statistics for retrieval metrics."""

    total_retrievals: int
    total_errors: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_result_count: float
    total_results: int
    errors_by_type: dict[str, int]
    retrievals_by_method: dict[str, int]


class RAGMetrics:
    """Tracks metrics for RAG retrieval operations.
    
    This class provides thread-safe tracking of retrieval metrics including:
    - Retrieval latency distribution (histogram)
    - Result count distribution
    - Cache hit rate (for future phases)
    - Error counts by type
    - Retrievals by method (fts, vector, hybrid)
    
    Metrics are stored in memory and can be exported for monitoring systems.
    Thread-safe for concurrent retrieval operations.
    """

    def __init__(self, max_history: int = 10000):
        """Initialize metrics tracker.
        
        Args:
            max_history: Maximum number of recent operations to keep in memory
        """
        self.max_history = max_history
        self._lock = threading.Lock()
        
        # Metrics storage
        self._history: list[RetrievalMetrics] = []
        self._latency_histogram: list[float] = []
        self._result_counts: list[int] = []
        self._errors_by_type: dict[str, int] = defaultdict(int)
        self._retrievals_by_method: dict[str, int] = defaultdict(int)
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        
        # Counters
        self._total_retrievals: int = 0
        self._total_errors: int = 0

    def record_retrieval(
        self,
        query: str,
        method: str,
        result_count: int,
        execution_time_ms: float,
        top_score: float | None = None,
        error: str | None = None,
    ) -> None:
        """Record a retrieval operation.
        
        Args:
            query: Search query (truncated if too long)
            method: Search method used (fts, vector, hybrid)
            result_count: Number of results returned
            execution_time_ms: Execution time in milliseconds
            top_score: Highest relevance score (if results exist)
            error: Error message if operation failed
        """
        with self._lock:
            # Truncate query for storage
            truncated_query = query[:100] if len(query) > 100 else query
            
            # Create metrics record
            metrics = RetrievalMetrics(
                query=truncated_query,
                method=method,
                result_count=result_count,
                execution_time_ms=execution_time_ms,
                top_score=top_score,
                error=error,
            )
            
            # Add to history (with size limit)
            self._history.append(metrics)
            if len(self._history) > self.max_history:
                self._history.pop(0)
            
            # Update metrics
            self._total_retrievals += 1
            self._retrievals_by_method[method] += 1
            self._latency_histogram.append(execution_time_ms)
            self._result_counts.append(result_count)
            
            # Track errors
            if error:
                self._total_errors += 1
                error_type = self._classify_error(error)
                self._errors_by_type[error_type] += 1
            
            # Trim histogram and result counts to max_history
            if len(self._latency_histogram) > self.max_history:
                self._latency_histogram.pop(0)
            if len(self._result_counts) > self.max_history:
                self._result_counts.pop(0)

    def record_cache_hit(self) -> None:
        """Record a cache hit (for future phases with caching)."""
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss (for future phases with caching)."""
        with self._lock:
            self._cache_misses += 1

    def get_summary(self) -> MetricsSummary:
        """Get summary statistics for all tracked metrics.
        
        Returns:
            MetricsSummary with aggregated statistics
        """
        with self._lock:
            if not self._latency_histogram:
                return MetricsSummary(
                    total_retrievals=0,
                    total_errors=0,
                    avg_latency_ms=0.0,
                    p50_latency_ms=0.0,
                    p95_latency_ms=0.0,
                    p99_latency_ms=0.0,
                    avg_result_count=0.0,
                    total_results=0,
                    errors_by_type={},
                    retrievals_by_method={},
                )
            
            # Calculate latency percentiles
            sorted_latencies = sorted(self._latency_histogram)
            n = len(sorted_latencies)
            
            p50_idx = int(n * 0.50)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)
            
            return MetricsSummary(
                total_retrievals=self._total_retrievals,
                total_errors=self._total_errors,
                avg_latency_ms=sum(self._latency_histogram) / len(self._latency_histogram),
                p50_latency_ms=sorted_latencies[p50_idx],
                p95_latency_ms=sorted_latencies[p95_idx],
                p99_latency_ms=sorted_latencies[p99_idx],
                avg_result_count=sum(self._result_counts) / len(self._result_counts),
                total_results=sum(self._result_counts),
                errors_by_type=dict(self._errors_by_type),
                retrievals_by_method=dict(self._retrievals_by_method),
            )

    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate (for future phases with caching).
        
        Returns:
            Cache hit rate as a percentage (0-100), or 0.0 if no cache operations
        """
        with self._lock:
            total = self._cache_hits + self._cache_misses
            if total == 0:
                return 0.0
            return (self._cache_hits / total) * 100

    def get_recent_operations(self, limit: int = 100) -> list[RetrievalMetrics]:
        """Get recent retrieval operations.
        
        Args:
            limit: Maximum number of operations to return
            
        Returns:
            List of recent RetrievalMetrics, most recent first
        """
        with self._lock:
            return list(reversed(self._history[-limit:]))

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format.
        
        Returns:
            Metrics formatted for Prometheus scraping
        """
        summary = self.get_summary()
        cache_hit_rate = self.get_cache_hit_rate()
        
        lines = [
            "# HELP rag_retrievals_total Total number of retrieval operations",
            "# TYPE rag_retrievals_total counter",
            f"rag_retrievals_total {summary.total_retrievals}",
            "",
            "# HELP rag_errors_total Total number of retrieval errors",
            "# TYPE rag_errors_total counter",
            f"rag_errors_total {summary.total_errors}",
            "",
            "# HELP rag_latency_ms Retrieval latency in milliseconds",
            "# TYPE rag_latency_ms summary",
            f"rag_latency_ms{{quantile=\"0.5\"}} {summary.p50_latency_ms}",
            f"rag_latency_ms{{quantile=\"0.95\"}} {summary.p95_latency_ms}",
            f"rag_latency_ms{{quantile=\"0.99\"}} {summary.p99_latency_ms}",
            f"rag_latency_ms_sum {sum(self._latency_histogram)}",
            f"rag_latency_ms_count {len(self._latency_histogram)}",
            "",
            "# HELP rag_result_count_avg Average number of results per retrieval",
            "# TYPE rag_result_count_avg gauge",
            f"rag_result_count_avg {summary.avg_result_count}",
            "",
            "# HELP rag_cache_hit_rate Cache hit rate percentage",
            "# TYPE rag_cache_hit_rate gauge",
            f"rag_cache_hit_rate {cache_hit_rate}",
            "",
        ]
        
        # Add per-method counters
        lines.append("# HELP rag_retrievals_by_method Retrievals by search method")
        lines.append("# TYPE rag_retrievals_by_method counter")
        for method, count in summary.retrievals_by_method.items():
            lines.append(f'rag_retrievals_by_method{{method="{method}"}} {count}')
        lines.append("")
        
        # Add per-error-type counters
        lines.append("# HELP rag_errors_by_type Errors by type")
        lines.append("# TYPE rag_errors_by_type counter")
        for error_type, count in summary.errors_by_type.items():
            lines.append(f'rag_errors_by_type{{type="{error_type}"}} {count}')
        lines.append("")
        
        return "\n".join(lines)

    def export_json(self) -> dict[str, Any]:
        """Export metrics as JSON-serializable dictionary.
        
        Returns:
            Dictionary with all metrics
        """
        summary = self.get_summary()
        
        return {
            "total_retrievals": summary.total_retrievals,
            "total_errors": summary.total_errors,
            "latency": {
                "avg_ms": summary.avg_latency_ms,
                "p50_ms": summary.p50_latency_ms,
                "p95_ms": summary.p95_latency_ms,
                "p99_ms": summary.p99_latency_ms,
            },
            "results": {
                "avg_count": summary.avg_result_count,
                "total_count": summary.total_results,
            },
            "cache": {
                "hit_rate_percent": self.get_cache_hit_rate(),
                "hits": self._cache_hits,
                "misses": self._cache_misses,
            },
            "errors_by_type": summary.errors_by_type,
            "retrievals_by_method": summary.retrievals_by_method,
        }

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._history.clear()
            self._latency_histogram.clear()
            self._result_counts.clear()
            self._errors_by_type.clear()
            self._retrievals_by_method.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._total_retrievals = 0
            self._total_errors = 0

    def _classify_error(self, error: str) -> str:
        """Classify error message into a type.
        
        Args:
            error: Error message
            
        Returns:
            Error type classification
        """
        error_lower = error.lower()
        
        if "timeout" in error_lower:
            return "timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "connection"
        elif "not found" in error_lower or "missing" in error_lower:
            return "not_found"
        elif "invalid" in error_lower or "validation" in error_lower:
            return "validation"
        elif "permission" in error_lower or "unauthorized" in error_lower:
            return "permission"
        else:
            return "unknown"


# Global metrics instance
_global_metrics: RAGMetrics | None = None
_metrics_lock = threading.Lock()


def get_metrics() -> RAGMetrics:
    """Get the global RAGMetrics instance.
    
    Returns:
        Global RAGMetrics instance (creates if not exists)
    """
    global _global_metrics
    
    with _metrics_lock:
        if _global_metrics is None:
            _global_metrics = RAGMetrics()
        return _global_metrics


def reset_metrics() -> None:
    """Reset the global metrics instance (useful for testing)."""
    global _global_metrics
    
    with _metrics_lock:
        if _global_metrics is not None:
            _global_metrics.reset()
