"""Unit tests for Citation entity, CitationRepository, CitationService.

Covers tasks.md tests for step 4:
- 4.1: attach_to_documents persists citations + usage atomically
- 4.2: Citation.format("APA") renders inline-style string
- 4.3: Citation.format("unknown") raises ValueError
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations
from models.citation import Citation
from repositories.citation_repo import CitationRepository
from services.citation_service import CitationService


@pytest.fixture
def service_factory(tmp_path: Path):
    factory = SQLiteConnectionFactory(str(tmp_path / "step4.db"))
    run_migrations(factory)
    repo = CitationRepository(factory)
    service = CitationService(repo, factory)
    return service, repo, factory


def _sample_citation(suffix: str = "1") -> Citation:
    return Citation(
        citation_id=f"cid-{suffix}",
        document_id=f"doc-{suffix}",
        chunk_id=None,
        source_type="document",
        title=f"Title {suffix}",
        author="Alice",
        created_at="2026-05-07T00:00:00+00:00",
        metadata={"k": "v"},
    )


def test_should_attach_citations_atomically_when_all_valid(service_factory) -> None:
    service, repo, factory = service_factory
    citations = [_sample_citation("1"), _sample_citation("2"), _sample_citation("3")]

    service.attach_to_documents(citations, query="hello", used_in_response=True)

    with factory.connect() as conn:
        cit_count = conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]
        usage_count = conn.execute("SELECT COUNT(*) FROM citation_usage").fetchone()[0]
    assert cit_count == 3
    assert usage_count == 3
    # Per-citation linkage
    for c in citations:
        loaded = repo.get(c.citation_id)
        assert loaded is not None
        assert loaded.title == c.title


def test_should_format_apa_when_style_is_apa() -> None:
    citation = _sample_citation("apa")

    rendered = citation.format("APA")

    assert citation.citation_id in rendered
    assert "Alice" in rendered
    assert "Title apa" in rendered
    assert "\n" not in rendered


def test_should_raise_when_format_style_unknown() -> None:
    citation = _sample_citation("err")
    with pytest.raises(ValueError, match="style"):
        citation.format("unknown")


def test_should_rollback_when_attach_fails_midway(service_factory) -> None:
    service, repo, factory = service_factory
    citations = [_sample_citation("a"), _sample_citation("b")]

    original_upsert = repo.upsert
    call_count = {"n": 0}

    def flaky_upsert(citation, *, conn=None):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise sqlite3.IntegrityError("kaboom")
        return original_upsert(citation, conn=conn)

    repo.upsert = flaky_upsert  # type: ignore[assignment]

    with pytest.raises(sqlite3.IntegrityError, match="kaboom"):
        service.attach_to_documents(citations, query="q", used_in_response=True)

    repo.upsert = original_upsert  # type: ignore[assignment]

    with factory.connect() as conn:
        cit_count = conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]
        usage_count = conn.execute("SELECT COUNT(*) FROM citation_usage").fetchone()[0]
    assert cit_count == 0
    assert usage_count == 0
