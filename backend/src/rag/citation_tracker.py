"""Backward-compat facade over CitationService + CitationRepository.

Public API (`Citation`, `CitationTracker`, `create_citation`, `get_citation`,
`format_citation`, `track_usage`, `soft_delete`, `get_source_document`) is
preserved so existing callers and tests keep working.

Logic now lives in:
- models/citation.py (Citation entity + format())
- repositories/citation_repo.py (SQL)
- services/citation_service.py (business logic + transactions)

This shim will be removed in step 7 once api/deps.py wires services directly.
"""

from __future__ import annotations

from typing import Any

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from models.citation import Citation
from repositories.citation_repo import CitationRepository
from services.citation_service import CitationService

__all__ = ["Citation", "CitationTracker"]


class CitationTracker:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._factory = SQLiteConnectionFactory(db_path)
        run_migrations(self._factory)
        self._repo = CitationRepository(self._factory)
        self._service = CitationService(self._repo, self._factory)

    def create_citation(
        self,
        document_id: str,
        chunk_id: str | None,
        source_type: str,
        title: str,
        author: str | None,
        created_at: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> Citation:
        return self._service.create_citation(
            document_id=document_id,
            chunk_id=chunk_id,
            source_type=source_type,
            title=title,
            author=author,
            created_at=created_at,
            metadata=metadata,
        )

    def format_citation(self, citation: Citation, style: str = "APA") -> str:
        return citation.format(style)

    def track_usage(
        self, citation_id: str, query: str, used_in_response: bool = True
    ) -> None:
        self._service.track_usage(citation_id, query, used_in_response)

    def get_citation(self, citation_id: str) -> Citation | None:
        return self._service.get_citation(citation_id)

    def soft_delete(self, citation_id: str) -> None:
        self._service.soft_delete(citation_id)

    def get_source_document(self, citation_id: str) -> dict[str, Any] | None:
        return self._service.get_source_document(citation_id)
