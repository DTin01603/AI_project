from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from agent.utils import parse_json_safe, truncate
from skills._base import BaseSkill
from skills._errors import SkillValidationError
from skills._prompt_loader import render


class Inputs(BaseModel):
    question: str
    documents: list[dict[str, Any]]


class Outputs(BaseModel):
    relevant_documents: list[dict[str, Any]] = []


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def _score_threshold(self) -> float:
        return float(self.config.get("fallback_score_threshold", 0.4))

    def _score_fallback(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        threshold = self._score_threshold()
        return [d for d in docs if d.get("score", 0) >= threshold]

    def invoke(self, inputs_dict: dict[str, Any], *, model_override: str | None = None) -> dict[str, Any]:
        inputs = self._validate_inputs(inputs_dict)
        docs = inputs.documents
        if not docs:
            return self._validate_outputs({"relevant_documents": []}).model_dump()

        docs_text = "\n\n".join(f"[{i + 1}] {truncate(d.get('content', ''))}" for i, d in enumerate(docs))

        try:
            template = self.prompt_source.get_template() if self.prompt_source else None
            if template is None:
                raise RuntimeError("grade_documents: prompt.md missing")
            rendered = render(template, {"question": inputs.question, "docs_text": docs_text})
            user_prompt = rendered.get("user", "")

            model = model_override or self.model
            if not model:
                raise RuntimeError("no model configured")
            adapter = self._resolve_adapter(model)
            output = adapter.invoke(
                model=model,
                messages=[("user", user_prompt)],
                constraints={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_output_tokens,
                },
            )
            parsed = parse_json_safe(output.answer_text or "")
            if not parsed or not isinstance(parsed.get("grades"), list):
                raise ValueError("invalid grades payload")

            relevant_indices = {
                g["index"] - 1
                for g in parsed["grades"]
                if isinstance(g, dict) and g.get("relevant") is True
            }
            relevant_docs = [docs[i] for i in sorted(relevant_indices) if 0 <= i < len(docs)]
            return self._validate_outputs({"relevant_documents": relevant_docs}).model_dump()

        except SkillValidationError:
            raise
        except Exception as exc:
            return self._validate_outputs({"relevant_documents": self._score_fallback(docs)}).model_dump()
