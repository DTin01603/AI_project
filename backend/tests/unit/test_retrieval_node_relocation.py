"""Smoke tests for the rag/retrieval_node.py -> agent/nodes/retrieval_node.py
move (Task 1 of improve-architecture-v2).

- 1.1: importing the relocated module works
- 1.2: the legacy `rag.retrieval_node` import path is gone everywhere
"""

from __future__ import annotations

from pathlib import Path


def test_should_import_retrieval_node_from_agent_when_renamed() -> None:
    from agent.nodes.retrieval_node import RetrievalNode  # noqa: F401

    # Sanity: the class exposes the same retrieve() entry point used by the
    # search router and graph nodes.
    assert hasattr(RetrievalNode, "retrieve")


def test_should_have_no_legacy_rag_retrieval_node_imports() -> None:
    """No file under backend/ may still import `rag.retrieval_node`."""
    repo_root = Path(__file__).resolve().parents[3]
    backend = repo_root / "backend"

    forbidden = ("from rag.retrieval_node", "import rag.retrieval_node")
    offenders: list[tuple[Path, int, str]] = []
    for py_file in backend.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(text, start=1):
            stripped = line.strip()
            if any(stripped.startswith(p) for p in forbidden):
                offenders.append((py_file, line_no, stripped))

    assert offenders == [], (
        "Legacy `rag.retrieval_node` import path still in use:\n"
        + "\n".join(f"  {p}:{ln}: {src}" for p, ln, src in offenders)
    )
