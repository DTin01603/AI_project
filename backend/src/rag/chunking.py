"""Chunking strategies for document indexing."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from rag.document_loader import Document


@dataclass
class Chunk:
    """A retrievable text segment derived from a source document."""

    id: str
    document_id: str
    text: str
    chunk_index: int
    start_offset: int
    end_offset: int
    metadata: dict[str, Any]


class ChunkingStrategy(ABC):
    """Base interface for chunking implementations."""

    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """Split one document into retrievable chunks."""


class RecursiveCharacterChunking(ChunkingStrategy):
    """Split text by paragraph/sentence/word boundaries with overlap."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        self.chunk_size = max(64, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

    def chunk(self, document: Document) -> list[Chunk]:
        text = document.text
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [self._build_chunk(document, 0, 0, len(text), text)]

        chunks: list[Chunk] = []
        start = 0
        idx = 0
        text_len = len(text)

        while start < text_len:
            target_end = min(start + self.chunk_size, text_len)
            end = self._find_breakpoint(text, start, target_end)
            if end <= start:
                end = target_end

            chunk_text = text[start:end]
            if chunk_text:
                chunks.append(self._build_chunk(document, idx, start, end, chunk_text))
                idx += 1

            if end >= text_len:
                break

            next_start = max(0, end - self.chunk_overlap)
            if next_start <= start:
                next_start = start + 1
            start = next_start

        return chunks

    def _find_breakpoint(self, text: str, start: int, target_end: int) -> int:
        window = text[start:target_end]

        paragraph_idx = window.rfind("\n\n")
        if paragraph_idx > int(0.5 * len(window)):
            return start + paragraph_idx + 2

        sentence_matches = list(re.finditer(r"[.!?]\s", window))
        if sentence_matches:
            match = sentence_matches[-1]
            if match.end() > int(0.5 * len(window)):
                return start + match.end()

        ws_idx = window.rfind(" ")
        if ws_idx > int(0.5 * len(window)):
            return start + ws_idx + 1

        return target_end

    @staticmethod
    def _build_chunk(document: Document, idx: int, start: int, end: int, text: str) -> Chunk:
        metadata = {
            "source_type": document.source_type,
            "file_name": document.metadata.file_name,
            "file_path": document.metadata.file_path,
            "chunk_strategy": "recursive",
            "document_metadata": document.metadata.extra,
        }
        return Chunk(
            id=f"{document.id}::chunk::{idx}",
            document_id=document.id,
            text=text,
            chunk_index=idx,
            start_offset=start,
            end_offset=end,
            metadata=metadata,
        )


class CodeAwareChunking(ChunkingStrategy):
    """Chunk code by definitions first, then fallback to recursive chunking."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        self.fallback = RecursiveCharacterChunking(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def chunk(self, document: Document) -> list[Chunk]:
        if document.source_type != "code_file":
            return self.fallback.chunk(document)

        lines = document.text.splitlines(keepends=True)
        if not lines:
            return []

        boundaries: list[int] = [0]
        signature_pattern = re.compile(r"^\s*(def\s+|async\s+def\s+|class\s+|function\s+|interface\s+|public\s+|private\s+|protected\s+)")

        offset = 0
        for line in lines:
            if signature_pattern.match(line) and offset not in boundaries:
                boundaries.append(offset)
            offset += len(line)

        boundaries = sorted(set(boundaries))
        boundaries.append(len(document.text))

        chunks: list[Chunk] = []
        for idx in range(len(boundaries) - 1):
            start = boundaries[idx]
            end = boundaries[idx + 1]
            segment = document.text[start:end]
            if not segment.strip():
                continue

            if len(segment) <= self.fallback.chunk_size:
                chunks.append(
                    Chunk(
                        id=f"{document.id}::chunk::{len(chunks)}",
                        document_id=document.id,
                        text=segment,
                        chunk_index=len(chunks),
                        start_offset=start,
                        end_offset=end,
                        metadata={
                            "source_type": document.source_type,
                            "file_name": document.metadata.file_name,
                            "file_path": document.metadata.file_path,
                            "chunk_strategy": "code-aware",
                            "document_metadata": document.metadata.extra,
                        },
                    )
                )
            else:
                sub_document = Document(
                    id=document.id,
                    text=segment,
                    metadata=document.metadata,
                    source_type=document.source_type,
                )
                sub_chunks = self.fallback.chunk(sub_document)
                for sub in sub_chunks:
                    sub.id = f"{document.id}::chunk::{len(chunks)}"
                    sub.chunk_index = len(chunks)
                    sub.start_offset += start
                    sub.end_offset += start
                    sub.metadata["chunk_strategy"] = "code-aware+recursive"
                    chunks.append(sub)

        if not chunks:
            return self.fallback.chunk(document)

        return chunks
