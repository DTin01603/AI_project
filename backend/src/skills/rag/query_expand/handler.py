from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from rag.query_expander import QueryExpander
from skills._base import BaseSkill


class Inputs(BaseModel):
    query: str
    max_alternatives: int | None = None


class Outputs(BaseModel):
    expansions: list[str] = []


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._expander = QueryExpander(
            max_expansions=int(self.config.get("max_expansions", 3)),
            timeout_ms=int(self.config.get("timeout_ms", 200)),
            cache_size=int(self.config.get("cache_size", 512)),
        )

    def run(self, inputs: Inputs) -> dict[str, Any]:
        expansions = self._expander.expand(inputs.query, max_alternatives=inputs.max_alternatives)
        return {"expansions": expansions}
