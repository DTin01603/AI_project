from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from skills._base import BaseSkill


class Inputs(BaseModel):
    question: str
    retry_count: int = 0
    history: list[dict[str, str]] = []


class Outputs(BaseModel):
    transformed_query: str


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def parse_output(self, raw: str, inputs: Inputs) -> dict[str, Any]:
        stripped = (raw or "").strip()
        return {"transformed_query": stripped or inputs.question}

    def fallback(self, inputs: Inputs, error: Exception) -> dict[str, Any]:
        return {"transformed_query": inputs.question}
