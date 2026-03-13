"""Search API endpoints for RAG retrieval operations.

This module provides HTTP endpoints for testing and debugging RAG retrieval:
- POST /api/search: Execute search with various parameters
- GET /api/search/health: Check FTS engine availability
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator

from rag.config import RAGConfig, load_config
from rag.fts_engine import FTSEngine
from rag.retrieval_node import RetrievalNode


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


# Pydantic Models

class SearchRequest(BaseModel):
    """Request model for search endpoint."""
    
    query: str = Field(
        ...,
        min_length=1,
        description="Search query text"
    )
    method: Literal["fts", "vector", "hybrid"] = Field(
        default="fts",
        description="Search method to use"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Offset for pagination"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Limit for pagination"
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata filters (conversation_id, date_range)"
    )
    
    @field_validator("query")
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        """Validate that query is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v


class SearchResult(BaseModel):
    """Individual search result."""
    
    id: str = Field(..., description="Document/message ID")
    content: str = Field(..., description="Document/message content")
    score: float = Field(..., description="Relevance score (0-1)")
    source_type: str = Field(..., description="Source type (conversation, document, code)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    
    results: list[SearchResult] = Field(
        default_factory=list,
        description="List of search results"
    )
    total_count: int = Field(
        ...,
        description="Total number of results before pagination"
    )
    query: str = Field(..., description="Original search query")
    method: str = Field(..., description="Search method used")
    execution_time_ms: float = Field(
        ...,
        description="Execution time in milliseconds"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: Literal["ok", "degraded", "error"] = Field(
        ...,
        description="Overall health status"
    )
    fts_available: bool = Field(
        ...,
        description="Whether FTS engine is available"
    )
    timestamp: str = Field(
        ...,
        description="Timestamp of health check (ISO format)"
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional health check details"
    )


# Dependency: Get RAG components

def get_rag_components() -> tuple[FTSEngine, RetrievalNode, RAGConfig]:
    """Get RAG components for request handling.
    
    Returns:
        Tuple of (FTSEngine, RetrievalNode, RAGConfig)
    """
    # Load configuration
    config = load_config()
    
    # Initialize FTS engine
    fts_engine = FTSEngine(db_path="./data/conversations.db")
    
    # Initialize retrieval node
    retrieval_node = RetrievalNode(fts_engine=fts_engine, config=config)
    
    return fts_engine, retrieval_node, config


# Endpoints

@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest, response: Response) -> SearchResponse:
    """Execute search and return results.
    
    Accepts a search query with various parameters and returns ranked results.
    Supports pagination with offset and limit parameters.
    
    Args:
        request: SearchRequest with query and search parameters
        response: FastAPI Response object for setting headers
        
    Returns:
        SearchResponse with results, metadata, and timing information
        
    Raises:
        HTTPException: 400 for invalid input, 500 for server errors
    """
    start_time = time.time()
    
    try:
        # Get RAG components
        fts_engine, retrieval_node, config = get_rag_components()
        
        # Phase 2b supports fts, vector, and hybrid retrieval.
        method = request.method
        
        # Execute retrieval (without pagination first to get total count)
        # Request more results than needed to support pagination
        retrieval_limit = request.offset + request.limit
        
        retrieved_docs = retrieval_node.retrieve(
            query=request.query,
            method=method,
            top_k=retrieval_limit,
            min_score=request.min_score,
            filters=request.filters,
        )
        
        # Get total count before pagination
        total_count = len(retrieved_docs)
        
        # Apply pagination
        paginated_docs = retrieved_docs[request.offset : request.offset + request.limit]
        
        # Convert to SearchResult models
        results = [
            SearchResult(
                id=doc.id,
                content=doc.content,
                score=doc.score,
                source_type=doc.source_type,
                metadata=doc.metadata,
            )
            for doc in paginated_docs
        ]
        
        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Add execution time to response headers (Requirement 3.6)
        response.headers["X-Execution-Time-Ms"] = f"{execution_time_ms:.2f}"
        
        # Build response
        search_response = SearchResponse(
            results=results,
            total_count=total_count,
            query=request.query,
            method=method,
            execution_time_ms=execution_time_ms,
        )
        
        logger.info(
            f"Search completed: query='{request.query[:50]}...', "
            f"method={method}, total={total_count}, "
            f"returned={len(results)}, time={execution_time_ms:.2f}ms"
        )
        
        return search_response
        
    except ValueError as e:
        # Input validation errors (Requirement 3.3: HTTP 400 for invalid requests)
        logger.warning(f"Invalid search request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Unexpected errors
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during search operation"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check status of search components.
    
    Verifies that the FTS engine is available and operational.
    Returns health status and component availability.
    
    Returns:
        HealthResponse with status and component availability
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    details: dict[str, Any] = {}
    
    try:
        # Get RAG components
        fts_engine, retrieval_node, config = get_rag_components()
        
        # Test FTS engine with a simple query
        try:
            # Execute a minimal search to verify FTS is working
            test_results = fts_engine.search(query="test", limit=1)
            fts_available = True
            details["fts_test"] = "passed"
        except Exception as e:
            fts_available = False
            details["fts_test"] = "failed"
            details["fts_error"] = str(e)
            logger.error(f"FTS health check failed: {e}")
        
        # Determine overall status
        if fts_available:
            status = "ok"
        else:
            status = "degraded"
        
        # Add configuration info
        details["default_search_method"] = config.default_search_method
        details["db_path"] = config.db_path
        
        return HealthResponse(
            status=status,
            fts_available=fts_available,
            timestamp=timestamp,
            details=details,
        )
        
    except Exception as e:
        # Critical error - can't even initialize components
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="error",
            fts_available=False,
            timestamp=timestamp,
            details={
                "error": str(e),
                "message": "Failed to initialize RAG components"
            },
        )

