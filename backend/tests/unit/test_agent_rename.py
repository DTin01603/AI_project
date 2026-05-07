"""Smoke tests for the research_agent/ -> agent/ rename (step 9 of refactor-architecture).

Covers tasks.md tests for step 9:
- 9.1: importing the renamed package works
- 9.2: no production code under backend/src/ still imports `research_agent`
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_should_import_agent_module_when_renamed() -> None:
    """The renamed package + the lightweight Database shim must be importable.

    `agent.graph` is intentionally NOT imported here: it transitively pulls
    optional LLM SDKs (groq, google-genai) which may be missing in the test
    environment. Importing the package and the Database shim is enough to
    prove the rename succeeded structurally.
    """
    import agent  # noqa: F401
    from agent.database import Database  # noqa: F401

    assert agent.__name__ == "agent"


def test_should_have_no_research_agent_imports_in_src() -> None:
    """Production code must not import the legacy `research_agent.` package.

    Tests are allowed to keep legacy filenames (e.g. test_research_agent_*.py)
    and the class name `ResearchAgentGraph` is intentionally preserved, so this
    check is scoped to actual import statements under backend/src/.
    """
    repo_root = Path(__file__).resolve().parents[3]
    src_dir = repo_root / "backend" / "src"

    forbidden_patterns = ["from research_agent.", "import research_agent."]
    offenders: list[tuple[Path, int, str]] = []
    for py_file in src_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(text, start=1):
            stripped = line.strip()
            if any(stripped.startswith(p) for p in forbidden_patterns):
                offenders.append((py_file, line_no, stripped))

    assert offenders == [], (
        "Production source still imports the legacy `research_agent` package:\n"
        + "\n".join(f"  {p}:{ln}: {src}" for p, ln, src in offenders)
    )
