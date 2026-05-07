"""Search API endpoints for RAG retrieval operations.

This module provides HTTP endpoints for testing and debugging RAG retrieval:
- POST /api/search: Execute search with various parameters
- GET /api/search/health: Check FTS engine availability
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Response

from api.deps import get_container
from api.schemas.search import (
    HealthResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from rag.config import RAGConfig
from rag.fts_engine import FTSEngine
from rag.retrieval_node import RetrievalNode


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


# Dependency: Get RAG components

def get_rag_components() -> tuple[FTSEngine, RetrievalNode, RAGConfig]:
    """Resolve shared RAG components from the AppContainer."""
    container = get_container()
    return container.fts_engine, container.retrieval_node, container.rag_config


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
        
        # Convert to SearchResultItem models
        results = [
            SearchResultItem(
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

