"""Smoke tests for the research_agent/ -> agent/ rename (step 9 of refactor-architecture).

Covers tasks.md tests for step 9:
- 9.1: importing the renamed package works
- 9.2: no production code under backend/src/ still imports `research_agent`
"""

from __future__ import annotations

from pathlib import Path


def test_should_import_agent_module_when_renamed() -> None:
    """The renamed `agent` package must still be importable.

    `agent.graph` is intentionally NOT imported here: it transitively pulls
    optional LLM SDKs (groq, google-genai) which may be missing in the test
    environment.
    """
    import agent  # noqa: F401

    assert agent.__name__ == "agent"


def test_should_have_no_research_agent_imports_in_src() -> None:
    """Production code must not import the legacy `research_agent.` package.

    Tests are allowed to keep legacy filenames (e.g. test_research_agent_*.py),
    so this check is scoped to actual import statements under backend/src/.
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


def test_should_have_no_legacy_agent_graph_class_in_src() -> None:
    """`ResearchAgentGraph` was renamed to `AgentGraph`; verify it's gone."""
    repo_root = Path(__file__).resolve().parents[3]
    src_dir = repo_root / "backend" / "src"

    offenders: list[tuple[Path, int, str]] = []
    for py_file in src_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(text, start=1):
            if "ResearchAgentGraph" in line:
                offenders.append((py_file, line_no, line.strip()))

    assert offenders == [], (
        "Production source still references `ResearchAgentGraph`:\n"
        + "\n".join(f"  {p}:{ln}: {src}" for p, ln, src in offenders)
    )
