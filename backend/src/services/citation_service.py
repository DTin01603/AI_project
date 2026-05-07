from __future__ import annotations

import hashlib
from typing import Any

from db.connection import SQLiteConnectionFactory
from models.citation import Citation
from repositories.citation_repo import CitationRepository


class CitationService:
    def __init__(
        self,
        citation_repo: CitationRepository,
        factory: SQLiteConnectionFactory,
    ) -> None:
        self._citations = citation_repo
        self._factory = factory

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
        citation = Citation(
            citation_id=self._stable_citation_id(document_id, chunk_id),
            document_id=document_id,
            chunk_id=chunk_id,
            source_type=source_type,
            title=title,
            author=author,
            created_at=created_at,
            metadata=metadata or {},
            available=True,
        )
        self._citations.upsert(citation)
        return citation

    def attach_to_documents(
        self,
        citations: list[Citation],
        query: str,
        used_in_response: bool = True,
    ) -> None:
        """Persist citations + their usage rows in one transaction."""
        with self._factory.transaction() as conn:
            for citation in citations:
                self._citations.upsert(citation, conn=conn)
                self._citations.insert_usage(
                    citation.citation_id,
                    query=query,
                    used_in_response=used_in_response,
                    conn=conn,
                )

    def track_usage(
        self,
        citation_id: str,
        query: str,
        used_in_response: bool = True,
    ) -> None:
        self._citations.insert_usage(citation_id, query, used_in_response)

    def get_citation(self, citation_id: str) -> Citation | None:
        return self._citations.get(citation_id)

    def soft_delete(self, citation_id: str) -> None:
        self._citations.soft_delete(citation_id)

    def get_source_document(self, citation_id: str) -> dict[str, Any] | None:
        citation = self._citations.get(citation_id)
        if citation is None:
            return None
        return {
            "citation_id": citation.citation_id,
            "document_id": citation.document_id,
            "chunk_id": citation.chunk_id,
            "source_type": citation.source_type,
            "title": citation.title,
            "available": citation.available,
            "metadata": citation.metadata,
        }

    @staticmethod
    def _stable_citation_id(document_id: str, chunk_id: str | None) -> str:
        seed = f"{document_id}::{chunk_id or ''}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
