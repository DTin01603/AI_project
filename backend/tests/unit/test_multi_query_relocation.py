"""Smoke tests for the rag/multi_query_retriever.py ->
services/multi_query_service.py move (Task 4)."""

from __future__ import annotations

from pathlib import Path


def test_should_import_multi_query_from_services() -> None:
    from services.multi_query_service import MultiQueryRetriever, MultiQueryResult  # noqa: F401

    assert hasattr(MultiQueryRetriever, "retrieve") or callable(MultiQueryRetriever)


def test_should_have_no_legacy_rag_multi_query_imports() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    backend = repo_root / "backend"

    forbidden = ("from rag.multi_query_retriever", "import rag.multi_query_retriever")
    offenders: list[tuple[Path, int, str]] = []
    for py_file in backend.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(text, start=1):
            stripped = line.strip()
            if any(stripped.startswith(p) for p in forbidden):
                offenders.append((py_file, line_no, stripped))

    assert offenders == [], (
        "Legacy `rag.multi_query_retriever` import path still in use:\n"
        + "\n".join(f"  {p}:{ln}: {src}" for p, ln, src in offenders)
    )
