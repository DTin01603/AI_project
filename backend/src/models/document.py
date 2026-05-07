from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentRecord:
    """Domain entity for an indexed document (one row in the `documents` table)."""

    id: str
    file_path: str
    file_name: str
    source_type: str
    file_size: int
    created_at: str
    modified_at: str
    indexed_at: str
    chunk_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexingResult:
    """Summary returned by DocumentIndexingService.index_document."""

    document_id: str
    file_path: str
    source_type: str
    chunk_count: int
