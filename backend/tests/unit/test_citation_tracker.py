"""Unit tests for citation tracker."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.citation_tracker import CitationTracker


def test_citation_tracker_create_and_get(tmp_path: Path):
    db_path = str(tmp_path / "citation.db")
    tracker = CitationTracker(db_path=db_path)

    citation = tracker.create_citation(
        document_id="doc-1",
        chunk_id="chunk-1",
        source_type="document",
        title="Design Doc",
        author="Alice",
        created_at="2026-03-09T00:00:00+00:00",
        metadata={"section": "intro"},
    )

    loaded = tracker.get_citation(citation.citation_id)

    assert loaded is not None
    assert loaded.citation_id == citation.citation_id
    assert loaded.title == "Design Doc"


def test_citation_tracker_format_and_soft_delete(tmp_path: Path):
    db_path = str(tmp_path / "citation2.db")
    tracker = CitationTracker(db_path=db_path)

    citation = tracker.create_citation(
        document_id="doc-2",
        chunk_id=None,
        source_type="conversation",
        title="Conversation Message",
        author=None,
        created_at=None,
        metadata={},
    )

    apa = tracker.format_citation(citation, style="APA")
    mla = tracker.format_citation(citation, style="MLA")
    chicago = tracker.format_citation(citation, style="Chicago")

    assert citation.citation_id in apa
    assert citation.citation_id in mla
    assert citation.citation_id in chicago

    tracker.track_usage(citation.citation_id, query="test query", used_in_response=True)
    tracker.soft_delete(citation.citation_id)

    loaded = tracker.get_citation(citation.citation_id)
    assert loaded is not None
    assert loaded.available is False
