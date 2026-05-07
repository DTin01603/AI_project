from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from research_agent.utils import parse_json_safe, truncate
from skills._base import BaseSkill
from skills._errors import SkillValidationError
from skills._prompt_loader import render


Grade = Literal["grounded_and_useful", "hallucination", "not_useful"]
_VALID_GRADES = {"grounded_and_useful", "hallucination", "not_useful"}


class Inputs(BaseModel):
    question: str
    generation: str
    context_docs: list[dict[str, Any]] = []


class Outputs(BaseModel):
    grade: Grade


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def invoke(self, inputs_dict: dict[str, Any], *, model_override: str | None = None) -> dict[str, Any]:
        inputs = self._validate_inputs(inputs_dict)
        # No context → cannot verify grounding; fail open
        if not inputs.context_docs:
            return self._validate_outputs({"grade": "grounded_and_useful"}).model_dump()

        context = "\n\n".join(truncate(d.get("content", ""), 400) for d in inputs.context_docs[:3])

        try:
            template = self.prompt_source.get_template() if self.prompt_source else None
            if template is None:
                raise RuntimeError("grade_generation: prompt.md missing")
            rendered = render(template, {
                "question": inputs.question,
                "context": context,
                "generation": truncate(inputs.generation, 600),
            })
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
            parsed = parse_json_safe(output.answer_text or "") or {}
            grade = parsed.get("grade", "grounded_and_useful")
            if grade not in _VALID_GRADES:
                grade = "grounded_and_useful"
            return self._validate_outputs({"grade": grade}).model_dump()

        except SkillValidationError:
            raise
        except Exception:
            # Fail open: accept on error
            return self._validate_outputs({"grade": "grounded_and_useful"}).model_dump()
