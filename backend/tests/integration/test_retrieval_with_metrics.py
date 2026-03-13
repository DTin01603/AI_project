"""Integration tests for retrieval with metrics tracking."""

import sys
import tempfile
from pathlib import Path

import pytest

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.config import RAGConfig
from rag.fts_engine import FTSEngine
from rag.metrics import RAGMetrics, reset_metrics
from rag.retrieval_node import RetrievalNode
from research_agent.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = Database(db_path)

    # Add some test messages
    conversation_id = db.create_conversation()
    db.save_message(
        conversation_id=conversation_id,
        role="user",
        content="How do I implement authentication in Python?",
    )
    db.save_message(
        conversation_id=conversation_id,
        role="assistant",
        content="To implement authentication in Python, you can use libraries like Flask-Login or Django's built-in authentication system.",
    )
    db.save_message(
        conversation_id=conversation_id,
        role="user",
        content="What about JWT tokens for API authentication?",
    )
    db.save_message(
        conversation_id=conversation_id,
        role="assistant",
        content="JWT tokens are great for API authentication. You can use PyJWT library to encode and decode tokens.",
    )

    yield db, db_path

    # Cleanup - just delete the file
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def retrieval_node_with_metrics(temp_db):
    """Create a retrieval node with metrics tracking."""
    db, db_path = temp_db

    # Reset global metrics before test
    reset_metrics()

    # Create FTS engine and retrieval node
    fts_engine = FTSEngine(db_path)
    config = RAGConfig(default_search_method="fts")
    metrics = RAGMetrics()

    node = RetrievalNode(fts_engine=fts_engine, config=config, metrics=metrics)

    yield node, metrics

    # No cleanup needed - FTSEngine and Database don't have close methods


def test_metrics_recorded_on_successful_retrieval(retrieval_node_with_metrics):
    """Test that metrics are recorded for successful retrieval."""
    node, metrics = retrieval_node_with_metrics

    # Execute retrieval
    state = {"messages": [{"content": "authentication Python"}]}
    result = node(state)

    # Verify retrieval worked
    assert "retrieved_documents" in result
    assert len(result["retrieved_documents"]) > 0

    # Verify metrics were recorded
    summary = metrics.get_summary()
    assert summary.total_retrievals == 1
    assert summary.total_errors == 0
    assert summary.avg_latency_ms > 0
    assert summary.retrievals_by_method["fts"] == 1

    # Verify recent operations
    recent = metrics.get_recent_operations(limit=1)
    assert len(recent) == 1
    assert recent[0].query == "authentication Python"
    assert recent[0].method == "fts"
    assert recent[0].result_count > 0
    assert recent[0].top_score is not None
    assert recent[0].error is None


def test_metrics_recorded_on_empty_query(retrieval_node_with_metrics):
    """Test that metrics are recorded even for empty queries."""
    node, metrics = retrieval_node_with_metrics

    # Execute retrieval with empty state
    state = {"messages": []}
    result = node(state)

    # Verify empty result
    assert result["retrieved_documents"] == []

    # Verify metrics were recorded with error
    summary = metrics.get_summary()
    assert summary.total_retrievals == 1
    assert summary.total_errors == 1

    # Verify error was classified
    recent = metrics.get_recent_operations(limit=1)
    assert len(recent) == 1
    assert recent[0].error == "No query found in state"


def test_metrics_accumulate_across_retrievals(retrieval_node_with_metrics):
    """Test that metrics accumulate across multiple retrievals."""
    node, metrics = retrieval_node_with_metrics

    # Execute multiple retrievals
    queries = [
        "authentication Python",
        "JWT tokens",
        "API authentication",
    ]

    for query in queries:
        state = {"messages": [{"content": query}]}
        node(state)

    # Verify metrics accumulated
    summary = metrics.get_summary()
    assert summary.total_retrievals == 3
    assert summary.total_errors == 0
    assert summary.retrievals_by_method["fts"] == 3

    # Verify all operations are in history
    recent = metrics.get_recent_operations(limit=10)
    assert len(recent) == 3


def test_metrics_export_json(retrieval_node_with_metrics):
    """Test exporting metrics as JSON."""
    node, metrics = retrieval_node_with_metrics

    # Execute retrieval
    state = {"messages": [{"content": "authentication"}]}
    node(state)

    # Export as JSON
    json_data = metrics.export_json()

    # Verify JSON structure
    assert "total_retrievals" in json_data
    assert "total_errors" in json_data
    assert "latency" in json_data
    assert "results" in json_data
    assert "cache" in json_data
    assert "retrievals_by_method" in json_data

    assert json_data["total_retrievals"] == 1
    assert json_data["latency"]["avg_ms"] > 0


def test_metrics_export_prometheus(retrieval_node_with_metrics):
    """Test exporting metrics in Prometheus format."""
    node, metrics = retrieval_node_with_metrics

    # Execute retrieval
    state = {"messages": [{"content": "authentication"}]}
    node(state)

    # Export as Prometheus
    prom_output = metrics.export_prometheus()

    # Verify Prometheus format
    assert "rag_retrievals_total 1" in prom_output
    assert "rag_errors_total 0" in prom_output
    assert 'rag_retrievals_by_method{method="fts"} 1' in prom_output
    assert "rag_latency_ms" in prom_output


def test_retrieval_metadata_includes_all_fields(retrieval_node_with_metrics):
    """Test that retrieval metadata includes all required fields."""
    node, metrics = retrieval_node_with_metrics

    # Execute retrieval
    state = {"messages": [{"content": "authentication Python"}]}
    result = node(state)

    # Verify metadata structure
    metadata = result["retrieval_metadata"]
    assert "query" in metadata
    assert "method" in metadata
    assert "result_count" in metadata
    assert "execution_time_ms" in metadata

    # Verify values
    assert metadata["query"] == "authentication Python"
    assert metadata["method"] == "fts"
    assert metadata["result_count"] > 0
    assert metadata["execution_time_ms"] > 0

    # Top score should be present if results exist
    if metadata["result_count"] > 0:
        assert "top_score" in metadata
        assert metadata["top_score"] > 0


def test_logging_includes_all_required_info(retrieval_node_with_metrics, caplog):
    """Test that logging includes all required information."""
    import logging

    caplog.set_level(logging.INFO)

    node, metrics = retrieval_node_with_metrics

    # Execute retrieval
    state = {"messages": [{"content": "authentication Python"}]}
    node(state)

    # Verify log message contains required fields
    log_messages = [record.message for record in caplog.records if record.levelname == "INFO"]
    assert len(log_messages) > 0

    # Find the retrieval completion log
    retrieval_logs = [msg for msg in log_messages if "Retrieval completed" in msg]
    assert len(retrieval_logs) == 1

    log_msg = retrieval_logs[0]
    assert "query=" in log_msg
    assert "method=" in log_msg
    assert "results=" in log_msg
    assert "time=" in log_msg
    assert "top_score=" in log_msg
