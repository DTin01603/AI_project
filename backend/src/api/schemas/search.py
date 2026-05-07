from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    """Request model for the /api/search endpoint."""

    query: str = Field(..., min_length=1, description="Search query text")
    method: Literal["fts", "vector", "hybrid"] = Field(
        default="fts", description="Search method to use"
    )
    top_k: int = Field(default=5, ge=1, le=100, description="Maximum number of results")
    min_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum relevance score threshold"
    )
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    limit: int = Field(default=10, ge=1, le=100, description="Limit for pagination")
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata filters (conversation_id, date_range)",
    )

    @field_validator("query")
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v


class SearchResultItem(BaseModel):
    """Individual search result row in a SearchResponse.

    Renamed from `SearchResult` to avoid clashing with the Domain entity
    `models.search.SearchResult` returned by repositories.
    """

    id: str = Field(..., description="Document/message ID")
    content: str = Field(..., description="Document/message content")
    score: float = Field(..., description="Relevance score (0-1)")
    source_type: str = Field(..., description="Source type")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchResponse(BaseModel):
    """Response model for the /api/search endpoint."""

    results: list[SearchResultItem] = Field(default_factory=list)
    total_count: int = Field(..., description="Total results before pagination")
    query: str = Field(..., description="Original search query")
    method: str = Field(..., description="Search method used")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")


class HealthResponse(BaseModel):
    """Response model for the /api/search/health endpoint."""

    status: Literal["ok", "degraded", "error"]
    fts_available: bool
    timestamp: str
    details: dict[str, Any] | None = None
