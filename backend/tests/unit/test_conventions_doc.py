"""Smoke test that docs/architecture/conventions.md exists and covers the
required sections (Task 10 of improve-architecture-v2).

This is a documentation task; there's no code logic to unit-test. The
smoke test guards against the doc being deleted or losing its key
sections in a future cleanup.
"""

from __future__ import annotations

from pathlib import Path


def test_should_have_conventions_doc_with_required_sections() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    doc = repo_root / "docs" / "architecture" / "conventions.md"

    assert doc.is_file(), f"Expected {doc} to exist"
    text = doc.read_text(encoding="utf-8")

    # Must mention the boundary explicitly.
    for keyword in ("Skill", "Service", "boundary", "anti-pattern"):
        assert keyword.lower() in text.lower(), (
            f"conventions.md must discuss {keyword!r}"
        )

    # Must be substantive — not a stub.
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    assert len(non_empty_lines) >= 30, (
        f"conventions.md is too short ({len(non_empty_lines)} non-empty lines)"
    )
