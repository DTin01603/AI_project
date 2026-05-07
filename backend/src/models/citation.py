from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_VALID_STYLES = frozenset({"APA", "MLA", "CHICAGO"})


@dataclass
class Citation:
    """Domain entity for a retrieved source.

    `format(style)` is a pure rendering helper kept here (Domain has no I/O).
    Style is case-insensitive; unknown styles raise ValueError.
    """

    citation_id: str
    document_id: str
    chunk_id: str | None
    source_type: str
    title: str
    author: str | None
    created_at: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    available: bool = True

    def format(self, style: str = "APA") -> str:
        style_upper = style.upper()
        if style_upper not in _VALID_STYLES:
            raise ValueError(
                f"Unknown citation style {style!r}; expected one of {sorted(_VALID_STYLES)}"
            )
        year = self._year()
        author = self.author or "Unknown"
        if style_upper == "MLA":
            return f'{author}. "{self.title}". {year}. [{self.citation_id}]'
        if style_upper == "CHICAGO":
            return f"{author}. {year}. {self.title}. Citation ID: {self.citation_id}."
        return f"{author} ({year}). {self.title}. [{self.citation_id}]"

    def _year(self) -> str:
        if not self.created_at:
            return "n.d."
        return self.created_at[:4]
