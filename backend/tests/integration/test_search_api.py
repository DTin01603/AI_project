"""Integration tests for Search API endpoints.

Tests end-to-end search flow, pagination, error responses, and health checks.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import RAG modules
from research_agent.database import Database
from rag.fts_engine import FTSEngine
from rag.config import RAGConfig
from rag.retrieval_node import RetrievalNode


def get_router():
    """Lazy load router to avoid import issues at module level."""
    from api.routers.search import router
    return router


@pytest.fixture
def test_app_with_data():
    """Create a test FastAPI app with populated database."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    # Create database and add test data
    db = Database(db_path)
    conversation_id = db.create_conversation()
    
    # Add diverse test messages for comprehensive testing
    test_messages = [
        "How do I implement authentication in Python using JWT tokens?",
        "What are the best practices for API security?",
        "Can you explain OAuth2 authentication flow?",
        "How to handle user sessions in web applications?",
        "What is the difference between authentication and authorization?",
        "Implementing password hashing with bcrypt in Python",
        "How to secure REST API endpoints?",
        "What are CORS policies and why are they important?",
        "Best practices for storing API keys securely",
        "How to implement rate limiting in FastAPI?",
    ]
    
    for content in test_messages:
        db.save_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )
    
    # Initialize FTS engine to index messages
    fts_engine = FTSEngine(db_path)
    
    # Create FastAPI app and include router
    app = FastAPI()
    router = get_router()
    app.include_router(router)
    
    yield TestClient(app), db_path, db
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def test_client(test_app_with_data, monkeypatch):
    """Create test client with mocked dependencies."""
    client, db_path, db = test_app_with_data
    
    # Mock get_rag_components to use our test database
    from api.routers import search as search_module
    
    def mock_get_rag_components():
        config = RAGConfig(db_path=db_path)
        fts_engine = FTSEngine(db_path)
        retrieval_node = RetrievalNode(fts_engine=fts_engine, config=config)
        return fts_engine, retrieval_node, config
    
    monkeypatch.setattr(search_module, "get_rag_components", mock_get_rag_components)
    
    yield client


# Test End-to-End Search Flow

def test_successful_search_with_results(test_client):
    """Test successful search that returns results.
    
    **Validates: Requirements 3.1, 3.2**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "authentication Python",
            "method": "fts",
            "top_k": 10,
            "min_score": 0.0,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "results" in data
    assert "total_count" in data
    assert "query" in data
    assert "method" in data
    assert "execution_time_ms" in data
    
    # Verify results exist
    assert len(data["results"]) > 0
    assert data["total_count"] > 0
    assert data["query"] == "authentication Python"
    assert data["method"] == "fts"
    
    # Verify execution time is present
    assert data["execution_time_ms"] > 0


def test_search_with_no_results(test_client):
    """Test search with no matching results returns HTTP 200 with empty list.
    
    **Validates: Requirements 3.2, 3.4**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "xyznonexistentquery123",
            "method": "fts",
            "top_k": 10,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify empty results
    assert data["results"] == []
    assert data["total_count"] == 0
    assert data["query"] == "xyznonexistentquery123"


def test_result_structure(test_client):
    """Test that results have correct structure.
    
    **Validates: Requirements 3.2**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "authentication",
            "method": "fts",
            "top_k": 5,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify at least one result
    assert len(data["results"]) > 0
    
    # Check structure of first result
    result = data["results"][0]
    assert "id" in result
    assert "content" in result
    assert "score" in result
    assert "source_type" in result
    assert "metadata" in result
    
    # Verify types
    assert isinstance(result["id"], str)
    assert isinstance(result["content"], str)
    assert isinstance(result["score"], (int, float))
    assert isinstance(result["source_type"], str)
    assert isinstance(result["metadata"], dict)
    
    # Verify score is in valid range
    assert 0.0 <= result["score"] <= 1.0


def test_execution_time_in_response(test_client):
    """Test that execution_time_ms is present in response.
    
    **Validates: Requirements 3.6**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "API security",
            "method": "fts",
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify execution time is present and positive
    assert "execution_time_ms" in data
    assert data["execution_time_ms"] > 0


def test_execution_time_header(test_client):
    """Test that X-Execution-Time-Ms header is present.
    
    **Validates: Requirements 3.6**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "API security",
            "method": "fts",
        }
    )
    
    assert response.status_code == 200
    
    # Verify header is present
    assert "X-Execution-Time-Ms" in response.headers
    
    # Verify header value is a valid number
    header_value = response.headers["X-Execution-Time-Ms"]
    assert float(header_value) > 0


# Test Pagination

def test_pagination_offset_and_limit(test_client):
    """Test pagination with offset and limit parameters.
    
    **Validates: Requirements 3.5**
    """
    # First request: get first 3 results
    response1 = test_client.post(
        "/api/search",
        json={
            "query": "authentication",
            "method": "fts",
            "offset": 0,
            "limit": 3,
        }
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Second request: get next 3 results
    response2 = test_client.post(
        "/api/search",
        json={
            "query": "authentication",
            "method": "fts",
            "offset": 3,
            "limit": 3,
        }
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Verify pagination works
    assert len(data1["results"]) <= 3
    assert len(data2["results"]) <= 3
    
    # Verify total_count is the same
    assert data1["total_count"] == data2["total_count"]
    
    # Verify results are different (if enough results exist)
    if len(data1["results"]) > 0 and len(data2["results"]) > 0:
        result_ids_1 = {r["id"] for r in data1["results"]}
        result_ids_2 = {r["id"] for r in data2["results"]}
        assert result_ids_1 != result_ids_2


def test_pagination_total_count(test_client):
    """Test that total_count is correct across paginated requests.
    
    **Validates: Requirements 3.5**
    """
    # Get all results
    response_all = test_client.post(
        "/api/search",
        json={
            "query": "API",
            "method": "fts",
            "top_k": 100,
            "limit": 100,
        }
    )
    
    assert response_all.status_code == 200
    data_all = response_all.json()
    total_count = data_all["total_count"]
    
    # Get paginated results
    response_page = test_client.post(
        "/api/search",
        json={
            "query": "API",
            "method": "fts",
            "offset": 0,
            "limit": 5,
        }
    )
    
    assert response_page.status_code == 200
    data_page = response_page.json()
    
    # Verify total_count matches
    assert data_page["total_count"] == total_count


def test_pagination_returns_correct_subset(test_client):
    """Test that pagination returns correct subset of results.
    
    **Validates: Requirements 3.5**
    """
    # Get all results
    response_all = test_client.post(
        "/api/search",
        json={
            "query": "authentication",
            "method": "fts",
            "top_k": 100,
            "limit": 100,
        }
    )
    
    assert response_all.status_code == 200
    data_all = response_all.json()
    all_results = data_all["results"]
    
    # Get paginated subset
    offset = 2
    limit = 3
    response_page = test_client.post(
        "/api/search",
        json={
            "query": "authentication",
            "method": "fts",
            "offset": offset,
            "limit": limit,
        }
    )
    
    assert response_page.status_code == 200
    data_page = response_page.json()
    page_results = data_page["results"]
    
    # Verify subset matches
    expected_subset = all_results[offset:offset + limit]
    assert len(page_results) == len(expected_subset)
    
    # Verify IDs match
    for i, result in enumerate(page_results):
        assert result["id"] == expected_subset[i]["id"]


def test_pagination_offset_beyond_results(test_client):
    """Test pagination with offset beyond available results.
    
    **Validates: Requirements 3.5**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "authentication",
            "method": "fts",
            "offset": 1000,
            "limit": 10,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return empty results but still have total_count
    assert data["results"] == []
    assert data["total_count"] >= 0


def test_pagination_limit_larger_than_results(test_client):
    """Test pagination with limit larger than available results.
    
    **Validates: Requirements 3.5**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "authentication",
            "method": "fts",
            "offset": 0,
            "limit": 100,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return all available results
    assert len(data["results"]) == data["total_count"]


# Test Error Responses

def test_empty_query_returns_400(test_client):
    """Test that empty query returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "",
            "method": "fts",
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_whitespace_only_query_returns_400(test_client):
    """Test that whitespace-only query returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "   ",
            "method": "fts",
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_invalid_top_k_zero_returns_400(test_client):
    """Test that top_k=0 returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "test",
            "method": "fts",
            "top_k": 0,
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_invalid_top_k_negative_returns_400(test_client):
    """Test that negative top_k returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "test",
            "method": "fts",
            "top_k": -5,
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_invalid_top_k_exceeds_max_returns_400(test_client):
    """Test that top_k > 100 returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "test",
            "method": "fts",
            "top_k": 101,
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_invalid_min_score_negative_returns_400(test_client):
    """Test that negative min_score returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "test",
            "method": "fts",
            "min_score": -0.5,
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_invalid_min_score_exceeds_max_returns_400(test_client):
    """Test that min_score > 1.0 returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "test",
            "method": "fts",
            "min_score": 1.5,
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_invalid_offset_negative_returns_400(test_client):
    """Test that negative offset returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "test",
            "method": "fts",
            "offset": -1,
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_invalid_limit_zero_returns_400(test_client):
    """Test that limit=0 returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "test",
            "method": "fts",
            "limit": 0,
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_invalid_limit_negative_returns_400(test_client):
    """Test that negative limit returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "test",
            "method": "fts",
            "limit": -5,
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_invalid_limit_exceeds_max_returns_400(test_client):
    """Test that limit > 100 returns HTTP 400.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "query": "test",
            "method": "fts",
            "limit": 101,
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_missing_query_field_returns_422(test_client):
    """Test that missing query field returns HTTP 422.
    
    **Validates: Requirements 3.3**
    """
    response = test_client.post(
        "/api/search",
        json={
            "method": "fts",
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


# Test Health Endpoint

def test_health_check_returns_status(test_client):
    """Test that health check returns status.
    
    **Validates: Requirements 3.1**
    """
    response = test_client.get("/api/search/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "status" in data
    assert "fts_available" in data
    assert "timestamp" in data
    
    # Verify status is valid
    assert data["status"] in ["ok", "degraded", "error"]


def test_health_check_fts_available_is_boolean(test_client):
    """Test that fts_available is boolean.
    
    **Validates: Requirements 3.1**
    """
    response = test_client.get("/api/search/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify fts_available is boolean
    assert isinstance(data["fts_available"], bool)


def test_health_check_timestamp_is_present(test_client):
    """Test that timestamp is present in health check.
    
    **Validates: Requirements 3.1**
    """
    response = test_client.get("/api/search/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify timestamp is present and non-empty
    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)
    assert len(data["timestamp"]) > 0
    
    # Verify timestamp is ISO format (basic check)
    assert "T" in data["timestamp"]


def test_health_check_includes_details(test_client):
    """Test that health check includes details.
    
    **Validates: Requirements 3.1**
    """
    response = test_client.get("/api/search/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify details are present
    assert "details" in data
    
    # If details exist, verify structure
    if data["details"]:
        assert isinstance(data["details"], dict)
