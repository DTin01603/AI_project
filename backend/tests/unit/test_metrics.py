"""Unit tests for RAG metrics tracking."""

import json
import sys
import threading
import time
from pathlib import Path

import pytest

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.metrics import RAGMetrics, RetrievalMetrics, get_metrics, reset_metrics


class TestRAGMetrics:
    """Test suite for RAGMetrics class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.metrics = RAGMetrics(max_history=100)

    def test_initialization(self):
        """Test metrics initialization."""
        assert self.metrics.max_history == 100
        assert self.metrics._total_retrievals == 0
        assert self.metrics._total_errors == 0
        assert len(self.metrics._history) == 0

    def test_record_retrieval_basic(self):
        """Test recording a basic retrieval operation."""
        self.metrics.record_retrieval(
            query="test query",
            method="fts",
            result_count=5,
            execution_time_ms=123.45,
            top_score=0.95,
        )

        assert self.metrics._total_retrievals == 1
        assert self.metrics._total_errors == 0
        assert len(self.metrics._history) == 1
        assert len(self.metrics._latency_histogram) == 1
        assert len(self.metrics._result_counts) == 1

        # Check recorded values
        record = self.metrics._history[0]
        assert record.query == "test query"
        assert record.method == "fts"
        assert record.result_count == 5
        assert record.execution_time_ms == 123.45
        assert record.top_score == 0.95
        assert record.error is None

    def test_record_retrieval_with_error(self):
        """Test recording a retrieval operation with error."""
        self.metrics.record_retrieval(
            query="failing query",
            method="fts",
            result_count=0,
            execution_time_ms=50.0,
            error="Connection timeout",
        )

        assert self.metrics._total_retrievals == 1
        assert self.metrics._total_errors == 1
        assert self.metrics._errors_by_type["timeout"] == 1

    def test_query_truncation(self):
        """Test that long queries are truncated."""
        long_query = "a" * 200
        self.metrics.record_retrieval(
            query=long_query,
            method="fts",
            result_count=1,
            execution_time_ms=10.0,
        )

        record = self.metrics._history[0]
        assert len(record.query) == 100
        assert record.query == "a" * 100

    def test_max_history_limit(self):
        """Test that history is limited to max_history."""
        metrics = RAGMetrics(max_history=10)

        # Record 20 operations
        for i in range(20):
            metrics.record_retrieval(
                query=f"query {i}",
                method="fts",
                result_count=1,
                execution_time_ms=10.0,
            )

        # Should only keep last 10
        assert len(metrics._history) == 10
        assert len(metrics._latency_histogram) == 10
        assert len(metrics._result_counts) == 10

        # But total count should be 20
        assert metrics._total_retrievals == 20

        # Check that we kept the most recent ones
        assert metrics._history[-1].query == "query 19"

    def test_error_classification(self):
        """Test error type classification."""
        test_cases = [
            ("Connection timeout", "timeout"),
            ("Network error occurred", "connection"),
            ("File not found", "not_found"),
            ("Invalid query syntax", "validation"),
            ("Permission denied", "permission"),
            ("Something went wrong", "unknown"),
        ]

        for error_msg, expected_type in test_cases:
            self.metrics.record_retrieval(
                query="test",
                method="fts",
                result_count=0,
                execution_time_ms=10.0,
                error=error_msg,
            )

        # Check error counts
        assert self.metrics._errors_by_type["timeout"] == 1
        assert self.metrics._errors_by_type["connection"] == 1
        assert self.metrics._errors_by_type["not_found"] == 1
        assert self.metrics._errors_by_type["validation"] == 1
        assert self.metrics._errors_by_type["permission"] == 1
        assert self.metrics._errors_by_type["unknown"] == 1

    def test_cache_tracking(self):
        """Test cache hit/miss tracking."""
        assert self.metrics.get_cache_hit_rate() == 0.0

        self.metrics.record_cache_hit()
        self.metrics.record_cache_hit()
        self.metrics.record_cache_miss()

        assert self.metrics._cache_hits == 2
        assert self.metrics._cache_misses == 1
        assert self.metrics.get_cache_hit_rate() == pytest.approx(66.67, rel=0.01)

    def test_get_summary_empty(self):
        """Test getting summary with no data."""
        summary = self.metrics.get_summary()

        assert summary.total_retrievals == 0
        assert summary.total_errors == 0
        assert summary.avg_latency_ms == 0.0
        assert summary.p50_latency_ms == 0.0
        assert summary.p95_latency_ms == 0.0
        assert summary.p99_latency_ms == 0.0
        assert summary.avg_result_count == 0.0
        assert summary.total_results == 0

    def test_get_summary_with_data(self):
        """Test getting summary with recorded data."""
        # Record various operations
        latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result_counts = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        for lat, count in zip(latencies, result_counts):
            self.metrics.record_retrieval(
                query="test",
                method="fts",
                result_count=count,
                execution_time_ms=lat,
            )

        summary = self.metrics.get_summary()

        assert summary.total_retrievals == 10
        assert summary.total_errors == 0
        assert summary.avg_latency_ms == 55.0
        # p50 at index 5 (50% of 10) = 60
        assert summary.p50_latency_ms == 60
        # p95 at index 9 (95% of 10) = 100
        assert summary.p95_latency_ms == 100
        # p99 at index 9 (99% of 10) = 100
        assert summary.p99_latency_ms == 100
        assert summary.avg_result_count == 5.5
        assert summary.total_results == 55
        assert summary.retrievals_by_method["fts"] == 10

    def test_get_summary_with_errors(self):
        """Test summary includes error counts."""
        self.metrics.record_retrieval(
            query="test1",
            method="fts",
            result_count=5,
            execution_time_ms=10.0,
        )
        self.metrics.record_retrieval(
            query="test2",
            method="fts",
            result_count=0,
            execution_time_ms=5.0,
            error="timeout",
        )

        summary = self.metrics.get_summary()

        assert summary.total_retrievals == 2
        assert summary.total_errors == 1
        assert summary.errors_by_type["timeout"] == 1

    def test_get_recent_operations(self):
        """Test getting recent operations."""
        # Record 10 operations
        for i in range(10):
            self.metrics.record_retrieval(
                query=f"query {i}",
                method="fts",
                result_count=i,
                execution_time_ms=float(i),
            )

        # Get last 5
        recent = self.metrics.get_recent_operations(limit=5)

        assert len(recent) == 5
        # Should be in reverse order (most recent first)
        assert recent[0].query == "query 9"
        assert recent[4].query == "query 5"

    def test_export_json(self):
        """Test exporting metrics as JSON."""
        self.metrics.record_retrieval(
            query="test",
            method="fts",
            result_count=5,
            execution_time_ms=100.0,
            top_score=0.9,
        )
        self.metrics.record_cache_hit()

        json_data = self.metrics.export_json()

        assert json_data["total_retrievals"] == 1
        assert json_data["total_errors"] == 0
        assert json_data["latency"]["avg_ms"] == 100.0
        assert json_data["results"]["avg_count"] == 5.0
        assert json_data["results"]["total_count"] == 5
        assert json_data["cache"]["hits"] == 1
        assert json_data["retrievals_by_method"]["fts"] == 1

        # Ensure it's JSON serializable
        json_str = json.dumps(json_data)
        assert isinstance(json_str, str)

    def test_export_prometheus(self):
        """Test exporting metrics in Prometheus format."""
        self.metrics.record_retrieval(
            query="test",
            method="fts",
            result_count=5,
            execution_time_ms=100.0,
        )

        prom_output = self.metrics.export_prometheus()

        assert "rag_retrievals_total 1" in prom_output
        assert "rag_errors_total 0" in prom_output
        assert 'rag_retrievals_by_method{method="fts"} 1' in prom_output
        assert "rag_latency_ms" in prom_output
        assert "rag_result_count_avg" in prom_output
        assert "rag_cache_hit_rate" in prom_output

    def test_reset(self):
        """Test resetting metrics."""
        # Record some data
        self.metrics.record_retrieval(
            query="test",
            method="fts",
            result_count=5,
            execution_time_ms=100.0,
        )
        self.metrics.record_cache_hit()

        assert self.metrics._total_retrievals == 1
        assert self.metrics._cache_hits == 1

        # Reset
        self.metrics.reset()

        assert self.metrics._total_retrievals == 0
        assert self.metrics._total_errors == 0
        assert self.metrics._cache_hits == 0
        assert self.metrics._cache_misses == 0
        assert len(self.metrics._history) == 0
        assert len(self.metrics._latency_histogram) == 0

    def test_thread_safety(self):
        """Test that metrics tracking is thread-safe."""
        metrics = RAGMetrics()
        num_threads = 10
        operations_per_thread = 100

        def record_operations():
            for i in range(operations_per_thread):
                metrics.record_retrieval(
                    query=f"query {i}",
                    method="fts",
                    result_count=i % 10,
                    execution_time_ms=float(i),
                )

        # Create and start threads
        threads = [threading.Thread(target=record_operations) for _ in range(num_threads)]
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify total count
        expected_total = num_threads * operations_per_thread
        assert metrics._total_retrievals == expected_total
        assert len(metrics._latency_histogram) <= metrics.max_history

    def test_retrievals_by_method(self):
        """Test tracking retrievals by method."""
        self.metrics.record_retrieval(
            query="test1", method="fts", result_count=1, execution_time_ms=10.0
        )
        self.metrics.record_retrieval(
            query="test2", method="vector", result_count=2, execution_time_ms=20.0
        )
        self.metrics.record_retrieval(
            query="test3", method="hybrid", result_count=3, execution_time_ms=30.0
        )
        self.metrics.record_retrieval(
            query="test4", method="fts", result_count=4, execution_time_ms=40.0
        )

        summary = self.metrics.get_summary()

        assert summary.retrievals_by_method["fts"] == 2
        assert summary.retrievals_by_method["vector"] == 1
        assert summary.retrievals_by_method["hybrid"] == 1


class TestGlobalMetrics:
    """Test suite for global metrics instance."""

    def test_get_metrics_singleton(self):
        """Test that get_metrics returns singleton instance."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2

    def test_reset_global_metrics(self):
        """Test resetting global metrics."""
        metrics = get_metrics()
        metrics.record_retrieval(
            query="test", method="fts", result_count=1, execution_time_ms=10.0
        )

        assert metrics._total_retrievals == 1

        reset_metrics()

        # Get metrics again (should be same instance, but reset)
        metrics = get_metrics()
        assert metrics._total_retrievals == 0


class TestRetrievalMetrics:
    """Test suite for RetrievalMetrics dataclass."""

    def test_creation(self):
        """Test creating RetrievalMetrics."""
        metrics = RetrievalMetrics(
            query="test query",
            method="fts",
            result_count=5,
            execution_time_ms=123.45,
            top_score=0.95,
        )

        assert metrics.query == "test query"
        assert metrics.method == "fts"
        assert metrics.result_count == 5
        assert metrics.execution_time_ms == 123.45
        assert metrics.top_score == 0.95
        assert metrics.error is None
        assert isinstance(metrics.timestamp, float)

    def test_creation_with_error(self):
        """Test creating RetrievalMetrics with error."""
        metrics = RetrievalMetrics(
            query="test",
            method="fts",
            result_count=0,
            execution_time_ms=10.0,
            error="Something went wrong",
        )

        assert metrics.error == "Something went wrong"
        assert metrics.top_score is None
