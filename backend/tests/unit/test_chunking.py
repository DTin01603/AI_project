"""Unit tests for chunking strategies."""

import sys
from pathlib import Path

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from rag.chunking import CodeAwareChunking, RecursiveCharacterChunking
from rag.document_loader import Document, DocumentMetadata


def _metadata(path: str, source_type: str) -> DocumentMetadata:
    return DocumentMetadata(
        file_name=Path(path).name,
        file_path=path,
        source_type=source_type,
        file_size=123,
        created_at="2026-01-01T00:00:00+00:00",
        modified_at="2026-01-01T00:00:00+00:00",
        file_extension=Path(path).suffix,
        extra={},
    )


def test_recursive_chunking_returns_single_chunk_for_short_text():
    doc = Document(
        id="doc-1",
        text="short text",
        metadata=_metadata("/tmp/a.txt", "document"),
        source_type="document",
    )

    chunks = RecursiveCharacterChunking(chunk_size=100, chunk_overlap=10).chunk(doc)

    assert len(chunks) == 1
    assert chunks[0].text == "short text"
    assert chunks[0].start_offset == 0
    assert chunks[0].end_offset == len("short text")


def test_recursive_chunking_creates_multiple_chunks_with_overlap():
    text = " ".join(f"token{i}" for i in range(80))
    doc = Document(
        id="doc-2",
        text=text,
        metadata=_metadata("/tmp/b.txt", "document"),
        source_type="document",
    )

    chunks = RecursiveCharacterChunking(chunk_size=120, chunk_overlap=20).chunk(doc)

    assert len(chunks) >= 2
    assert chunks[1].start_offset < chunks[0].end_offset


def test_code_aware_chunking_splits_by_definitions():
    code = (
        "def alpha():\n"
        "    return 1\n\n"
        "def beta():\n"
        "    return 2\n"
    )
    doc = Document(
        id="doc-3",
        text=code,
        metadata=_metadata("/tmp/c.py", "code_file"),
        source_type="code_file",
    )

    chunks = CodeAwareChunking(chunk_size=100, chunk_overlap=10).chunk(doc)

    assert len(chunks) >= 2
    assert any("alpha" in c.text for c in chunks)
    assert any("beta" in c.text for c in chunks)
