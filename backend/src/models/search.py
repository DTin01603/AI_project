from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SearchResult:
    """Result row from a full-text or hybrid search.

    Mirrors the legacy rag.fts_engine.SearchResult so callers (HybridSearchEngine,
    RetrievalNode, MultiQueryRetriever, Reranker) do not need to change while the
    refactor migrates them to repositories. After step 7 the legacy import path
    will be removed.
    """

    id: str
    content: str
    score: float
    metadata: dict[str, Any]
    source_type: str = "conversation"


@dataclass(frozen=True)
class RetrievedDocument:
    id: str
    content: str
    score: float
    metadata: dict[str, Any]
