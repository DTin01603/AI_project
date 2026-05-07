"""Smoke tests for the rag/subgraph/ -> agent/subgraph/ move (Task 2)."""

from __future__ import annotations

from pathlib import Path


def test_should_have_subgraph_package_at_agent_subgraph() -> None:
    """The subgraph package must exist under agent/.

    We don't import RAGSubgraph here because subgraph.nodes pulls in `skills`
    which transitively requires jinja2 — not always present in unit-test
    environments. The integration tests cover the full import path.
    """
    repo_root = Path(__file__).resolve().parents[3]
    new_path = repo_root / "backend" / "src" / "agent" / "subgraph"
    old_path = repo_root / "backend" / "src" / "rag" / "subgraph"

    assert new_path.is_dir(), f"Expected {new_path} to exist after Task 2"
    assert (new_path / "__init__.py").is_file()
    assert (new_path / "graph.py").is_file()
    assert not old_path.exists(), f"Legacy {old_path} must be gone after Task 2"


def test_should_have_no_legacy_rag_subgraph_imports() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    backend = repo_root / "backend"

    forbidden = ("from rag.subgraph", "import rag.subgraph")
    offenders: list[tuple[Path, int, str]] = []
    for py_file in backend.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(text, start=1):
            stripped = line.strip()
            if any(stripped.startswith(p) for p in forbidden):
                offenders.append((py_file, line_no, stripped))

    assert offenders == [], (
        "Legacy `rag.subgraph` import path still in use:\n"
        + "\n".join(f"  {p}:{ln}: {src}" for p, ln, src in offenders)
    )
