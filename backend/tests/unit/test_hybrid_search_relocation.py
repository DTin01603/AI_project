"""Smoke tests for the rag/hybrid_search.py -> services/hybrid_search_service.py
move (Task 3 of improve-architecture-v2).

The class name `HybridSearchEngine` is intentionally kept for now; only the
module path was renamed. A class rename can come in a later PR if desired.
"""

from __future__ import annotations

from pathlib import Path


def test_should_import_hybrid_search_from_services() -> None:
    from services.hybrid_search_service import HybridSearchEngine  # noqa: F401

    assert hasattr(HybridSearchEngine, "search")


def test_should_have_no_legacy_rag_hybrid_search_imports_in_python_code() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    backend = repo_root / "backend"

    forbidden = ("from rag.hybrid_search", "import rag.hybrid_search")
    offenders: list[tuple[Path, int, str]] = []
    for py_file in backend.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(text, start=1):
            stripped = line.strip()
            if any(stripped.startswith(p) for p in forbidden):
                offenders.append((py_file, line_no, stripped))

    assert offenders == [], (
        "Legacy `rag.hybrid_search` import path still in use:\n"
        + "\n".join(f"  {p}:{ln}: {src}" for p, ln, src in offenders)
    )
