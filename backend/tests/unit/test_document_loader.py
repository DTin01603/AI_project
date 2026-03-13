"""Unit tests for document loaders."""

import sys
from pathlib import Path

import pytest

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.document_loader import CodeLoader, DocumentLoadError, MarkdownLoader, TextLoader, load_document


def test_text_loader_reads_plain_text(tmp_path: Path):
    target = tmp_path / "note.txt"
    target.write_text("alpha\nbeta\n", encoding="utf-8")

    doc = TextLoader().load(target)

    assert doc.text.replace("\r\n", "\n") == "alpha\nbeta\n"
    assert doc.source_type == "document"
    assert doc.metadata.file_name == "note.txt"


def test_markdown_loader_extracts_frontmatter(tmp_path: Path):
    target = tmp_path / "guide.md"
    target.write_text(
        "---\ntitle: Sample\nauthor: tester\n---\n# Heading\nbody", encoding="utf-8"
    )

    doc = MarkdownLoader().load(target)

    assert doc.text.startswith("# Heading")
    assert doc.metadata.extra["frontmatter"]["title"] == "Sample"


def test_code_loader_tags_source_type(tmp_path: Path):
    target = tmp_path / "service.py"
    target.write_text('"""Doc"""\n\ndef add(a, b):\n    return a + b\n', encoding="utf-8")

    doc = CodeLoader().load(target)

    assert doc.source_type == "code_file"
    assert doc.metadata.extra["language"] == "py"
    assert any(sig.startswith("def add") for sig in doc.metadata.extra["signatures"])


def test_load_document_rejects_unsupported_format(tmp_path: Path):
    target = tmp_path / "archive.bin"
    target.write_bytes(b"\x00\x01\x02")

    with pytest.raises(DocumentLoadError, match="Unsupported document format"):
        load_document(target)
