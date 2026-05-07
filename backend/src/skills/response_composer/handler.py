from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from skills._base import BaseSkill


class Inputs(BaseModel):
    question: str
    knowledge_base: str


class Outputs(BaseModel):
    answer: str


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def invoke(self, inputs_dict: dict[str, Any], *, model_override: str | None = None) -> dict[str, Any]:
        kb = (inputs_dict.get("knowledge_base") or "").strip()
        if not kb:
            return self.Outputs(answer="Mình chưa thu thập đủ dữ liệu để trả lời chắc chắn.").model_dump()
        return super().invoke(inputs_dict, model_override=model_override)

    def parse_output(self, raw: str, inputs: Inputs) -> dict[str, Any]:
        answer = (raw or "").strip()
        if not answer:
            return {"answer": inputs.knowledge_base}
        return {"answer": answer}

    def fallback(self, inputs: Inputs, error: Exception) -> dict[str, Any]:
        return {"answer": inputs.knowledge_base}
