"""Unit tests for RetrievalNode class."""

import sys
import tempfile
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.config import RAGConfig
from rag.fts_engine import FTSEngine
from rag.retrieval_node import RetrievalNode
from research_agent.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        db = Database(db_path)
        
        # Create a conversation and add some messages
        conv_id = db.create_conversation()
        db.save_message(conv_id, "user", "How do I deploy my application?")
        db.save_message(conv_id, "assistant", "You can deploy using Docker containers.")
        db.save_message(conv_id, "user", "What about authentication?")
        db.save_message(conv_id, "assistant", "Use OAuth2 for authentication.")
        
        yield db_path


@pytest.fixture
def fts_engine(temp_db):
    """Create FTS engine with test database."""
    return FTSEngine(temp_db)


@pytest.fixture
def retrieval_node(fts_engine):
    """Create retrieval node with test configuration."""
    config = RAGConfig(
        default_search_method="fts",
        default_top_k=5,
        min_relevance_score=0.0,
    )
    return RetrievalNode(fts_engine=fts_engine, config=config)


def test_retrieval_node_initialization(fts_engine):
    """Test that RetrievalNode initializes correctly."""
    node = RetrievalNode(fts_engine=fts_engine)
    
    assert node.fts_engine is fts_engine
    assert node.config is not None
    assert node.vector_search is not None


def test_retrieval_node_with_custom_config(fts_engine):
    """Test RetrievalNode with custom configuration."""
    config = RAGConfig(
        default_search_method="fts",
        default_top_k=10,
        min_relevance_score=0.5,
    )
    node = RetrievalNode(fts_engine=fts_engine, config=config)
    
    assert node.config.default_top_k == 10
    assert node.config.min_relevance_score == 0.5


def test_extract_query_from_human_message(retrieval_node):
    """Test extracting query from HumanMessage."""
    state = {
        "messages": [
            HumanMessage(content="What is authentication?"),
        ]
    }
    
    query = retrieval_node._extract_query(state)
    assert query == "What is authentication?"


def test_extract_query_from_multiple_messages(retrieval_node):
    """Test extracting query from last message when multiple exist."""
    state = {
        "messages": [
            HumanMessage(content="First message"),
            HumanMessage(content="Second message"),
            HumanMessage(content="Last message"),
        ]
    }
    
    query = retrieval_node._extract_query(state)
    assert query == "Last message"


def test_extract_query_from_dict_message(retrieval_node):
    """Test extracting query from dictionary message format."""
    state = {
        "messages": [
            {"role": "user", "content": "Query from dict"},
        ]
    }
    
    query = retrieval_node._extract_query(state)
    assert query == "Query from dict"


def test_extract_query_empty_messages(retrieval_node):
    """Test extracting query when no messages exist."""
    state = {"messages": []}
    
    query = retrieval_node._extract_query(state)
    assert query == ""


def test_retrieve_fts_basic(retrieval_node):
    """Test basic FTS retrieval."""
    results = retrieval_node.retrieve(
        query="deploy",
        method="fts",
        top_k=5,
        min_score=0.0,
    )
    
    assert len(results) > 0
    assert all(hasattr(r, "id") for r in results)
    assert all(hasattr(r, "content") for r in results)
    assert all(hasattr(r, "score") for r in results)
    assert all(0.0 <= r.score <= 1.0 for r in results)


def test_retrieve_fts_with_min_score(retrieval_node):
    """Test FTS retrieval with minimum score threshold."""
    results = retrieval_node.retrieve(
        query="deploy",
        method="fts",
        top_k=5,
        min_score=0.5,
    )
    
    # All results should meet minimum score
    assert all(r.score >= 0.5 for r in results)


def test_retrieve_fts_with_top_k_limit(retrieval_node):
    """Test FTS retrieval respects top_k limit."""
    results = retrieval_node.retrieve(
        query="authentication",
        method="fts",
        top_k=2,
        min_score=0.0,
    )
    
    assert len(results) <= 2


def test_retrieve_empty_query(retrieval_node):
    """Test retrieval with empty query returns empty results."""
    results = retrieval_node.retrieve(
        query="",
        method="fts",
        top_k=5,
        min_score=0.0,
    )
    
    assert results == []


def test_retrieve_vector_basic(retrieval_node):
    """Test vector retrieval returns valid results structure."""
    results = retrieval_node.retrieve(
        query="deploy",
        method="vector",
        top_k=5,
        min_score=0.0,
    )

    assert isinstance(results, list)
    if results:
        assert all(hasattr(r, "id") for r in results)
        assert all(hasattr(r, "content") for r in results)
        assert all(hasattr(r, "score") for r in results)
        assert all(0.0 <= r.score <= 1.0 for r in results)


def test_retrieve_hybrid_basic(retrieval_node):
    """Test hybrid retrieval returns valid results structure."""
    results = retrieval_node.retrieve(
        query="authentication",
        method="hybrid",
        top_k=5,
        min_score=0.0,
    )

    assert isinstance(results, list)
    if results:
        assert all(hasattr(r, "id") for r in results)
        assert all(hasattr(r, "content") for r in results)
        assert all(hasattr(r, "score") for r in results)
        assert all(0.0 <= r.score <= 1.0 for r in results)


def test_retrieve_invalid_method(retrieval_node):
    """Test that invalid search method raises ValueError."""
    with pytest.raises(ValueError, match="Unknown search method"):
        retrieval_node.retrieve(
            query="test",
            method="invalid",  # type: ignore
            top_k=5,
            min_score=0.0,
        )


def test_call_method_basic(retrieval_node):
    """Test __call__ method with basic state."""
    state = {
        "messages": [
            HumanMessage(content="deploy application"),
        ]
    }
    
    result = retrieval_node(state)
    
    assert "retrieved_documents" in result
    assert "retrieval_metadata" in result
    assert isinstance(result["retrieved_documents"], list)
    assert isinstance(result["retrieval_metadata"], dict)


def test_call_method_metadata(retrieval_node):
    """Test __call__ method returns correct metadata."""
    state = {
        "messages": [
            HumanMessage(content="authentication"),
        ]
    }
    
    result = retrieval_node(state)
    metadata = result["retrieval_metadata"]
    
    assert metadata["query"] == "authentication"
    assert metadata["method"] == "fts"
    assert metadata["result_count"] >= 0
    assert metadata["execution_time_ms"] >= 0.0
    
    # If results exist, top_score should be present
    if result["retrieved_documents"]:
        assert "top_score" in metadata
        assert 0.0 <= metadata["top_score"] <= 1.0


def test_call_method_empty_messages(retrieval_node):
    """Test __call__ method with empty messages."""
    state = {"messages": []}
    
    result = retrieval_node(state)
    
    assert result["retrieved_documents"] == []
    assert result["retrieval_metadata"]["result_count"] == 0
    assert result["retrieval_metadata"]["query"] == ""


def test_call_method_no_matching_results(retrieval_node):
    """Test __call__ method when query has no matches."""
    state = {
        "messages": [
            HumanMessage(content="xyzabc123nonexistent"),
        ]
    }
    
    result = retrieval_node(state)
    
    assert result["retrieved_documents"] == []
    assert result["retrieval_metadata"]["result_count"] == 0


def test_retrieved_document_structure(retrieval_node):
    """Test that retrieved documents have correct structure."""
    results = retrieval_node.retrieve(
        query="deploy",
        method="fts",
        top_k=5,
        min_score=0.0,
    )
    
    if results:
        doc = results[0]
        assert hasattr(doc, "id")
        assert hasattr(doc, "content")
        assert hasattr(doc, "score")
        assert hasattr(doc, "source_type")
        assert hasattr(doc, "metadata")
        assert isinstance(doc.metadata, dict)


def test_results_ordered_by_score(retrieval_node):
    """Test that results are ordered by descending score."""
    results = retrieval_node.retrieve(
        query="deploy authentication",
        method="fts",
        top_k=5,
        min_score=0.0,
    )
    
    if len(results) > 1:
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# Task 3.3: Additional tests for state integration, empty results, and performance
# ============================================================================


def test_state_integration_adds_documents_to_state(retrieval_node, temp_db):
    """Test that retrieval node properly adds documents to state.
    
    Validates Requirement 2.4: Return empty result set when no results meet threshold.
    """
    # Test with query that should return results
    state = {
        "messages": [HumanMessage(content="deploy")],
        "existing_key": "should_be_preserved",
    }
    
    result = retrieval_node(state)
    
    # Verify state structure
    assert "retrieved_documents" in result
    assert "retrieval_metadata" in result
    
    # Verify existing state is not modified (only new keys added)
    # Note: LangGraph nodes typically return only the updates, not full state
    assert "existing_key" not in result  # Node returns only updates
    
    # Verify documents structure
    docs = result["retrieved_documents"]
    assert isinstance(docs, list)
    
    if docs:  # If results found
        for doc in docs:
            assert hasattr(doc, "id")
            assert hasattr(doc, "content")
            assert hasattr(doc, "score")
            assert hasattr(doc, "source_type")
            assert hasattr(doc, "metadata")


def test_state_integration_with_high_min_score_returns_empty(retrieval_node):
    """Test that high min_score threshold returns empty results.
    
    Validates Requirement 2.4: Return empty result set when no results meet threshold.
    """
    # Configure node with high minimum score
    config = RAGConfig(
        default_search_method="fts",
        default_top_k=5,
        min_relevance_score=0.99,  # Very high threshold
    )
    node = RetrievalNode(fts_engine=retrieval_node.fts_engine, config=config)
    
    state = {
        "messages": [HumanMessage(content="deploy")],
    }
    
    result = node(state)
    
    # Should return empty results due to high threshold
    assert result["retrieved_documents"] == []
    assert result["retrieval_metadata"]["result_count"] == 0


def test_empty_result_handling_no_matches(retrieval_node):
    """Test handling of queries with no matching documents.
    
    Validates Requirement 2.4: Return empty result set appropriately.
    """
    # Query with nonsense text that won't match anything
    results = retrieval_node.retrieve(
        query="xyznonexistentquery123456",
        method="fts",
        top_k=5,
        min_score=0.0,
    )
    
    assert results == []
    assert isinstance(results, list)


def test_empty_result_handling_whitespace_query(retrieval_node):
    """Test handling of whitespace-only queries."""
    results = retrieval_node.retrieve(
        query="   \t\n  ",
        method="fts",
        top_k=5,
        min_score=0.0,
    )
    
    assert results == []


def test_empty_result_handling_in_state(retrieval_node):
    """Test that empty results are properly added to state."""
    state = {
        "messages": [HumanMessage(content="xyznonexistent")],
    }
    
    result = retrieval_node(state)
    
    assert result["retrieved_documents"] == []
    assert result["retrieval_metadata"]["result_count"] == 0
    assert result["retrieval_metadata"]["query"] == "xyznonexistent"
    assert "top_score" not in result["retrieval_metadata"]


def test_performance_typical_query_under_500ms(retrieval_node):
    """Test that typical queries complete within 500ms.
    
    Validates Requirement 2.5: Complete retrieval operations within 500ms.
    """
    import time
    
    # Execute a typical query
    start_time = time.time()
    results = retrieval_node.retrieve(
        query="deploy application",
        method="fts",
        top_k=5,
        min_score=0.0,
    )
    execution_time_ms = (time.time() - start_time) * 1000
    
    # Verify performance requirement
    assert execution_time_ms < 500, (
        f"Query took {execution_time_ms:.2f}ms, exceeds 500ms requirement"
    )


def test_performance_state_call_under_500ms(retrieval_node):
    """Test that state-based retrieval completes within 500ms.
    
    Validates Requirement 2.5: Complete retrieval operations within 500ms.
    """
    import time
    
    state = {
        "messages": [HumanMessage(content="authentication OAuth2")],
    }
    
    start_time = time.time()
    result = retrieval_node(state)
    execution_time_ms = (time.time() - start_time) * 1000
    
    # Verify performance requirement
    assert execution_time_ms < 500, (
        f"State call took {execution_time_ms:.2f}ms, exceeds 500ms requirement"
    )
    
    # Also verify the metadata reports reasonable time
    reported_time = result["retrieval_metadata"]["execution_time_ms"]
    assert reported_time < 500


def test_performance_empty_query_fast(retrieval_node):
    """Test that empty queries are handled quickly."""
    import time
    
    start_time = time.time()
    results = retrieval_node.retrieve(
        query="",
        method="fts",
        top_k=5,
        min_score=0.0,
    )
    execution_time_ms = (time.time() - start_time) * 1000
    
    # Empty queries should be very fast (< 10ms)
    assert execution_time_ms < 10
    assert results == []


def test_state_integration_preserves_metadata_fields(retrieval_node):
    """Test that all required metadata fields are present in state."""
    state = {
        "messages": [HumanMessage(content="deploy")],
    }
    
    result = retrieval_node(state)
    metadata = result["retrieval_metadata"]
    
    # Required fields
    assert "query" in metadata
    assert "method" in metadata
    assert "result_count" in metadata
    assert "execution_time_ms" in metadata
    
    # Verify types
    assert isinstance(metadata["query"], str)
    assert isinstance(metadata["method"], str)
    assert isinstance(metadata["result_count"], int)
    assert isinstance(metadata["execution_time_ms"], float)
    
    # top_score is optional (only present when results exist)
    if result["retrieved_documents"]:
        assert "top_score" in metadata
        assert isinstance(metadata["top_score"], float)


def test_state_integration_multiple_retrievals(retrieval_node):
    """Test that multiple retrieval calls work correctly."""
    # First retrieval
    state1 = {
        "messages": [HumanMessage(content="deploy")],
    }
    result1 = retrieval_node(state1)
    
    # Second retrieval with different query
    state2 = {
        "messages": [HumanMessage(content="authentication")],
    }
    result2 = retrieval_node(state2)
    
    # Verify both work independently
    assert result1["retrieval_metadata"]["query"] == "deploy"
    assert result2["retrieval_metadata"]["query"] == "authentication"
    
    # Results should be different (unless by coincidence)
    # At minimum, metadata should differ
    assert result1["retrieval_metadata"] != result2["retrieval_metadata"]
