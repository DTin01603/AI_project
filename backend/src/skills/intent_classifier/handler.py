from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from skills._base import BaseSkill
from skills._prompt_loader import render

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

Intent = Literal["direct_answer", "local_rag", "web_search", "current_date"]
_VALID_INTENTS = {"direct_answer", "local_rag", "web_search", "current_date"}


def _extract_json(raw: str) -> dict[str, Any]:
    stripped = (raw or "").strip()
    fence_match = _FENCE_RE.match(stripped)
    if fence_match:
        stripped = fence_match.group(1).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        obj_match = _OBJECT_RE.search(stripped)
        if obj_match:
            return json.loads(obj_match.group(0))
        raise


class Inputs(BaseModel):
    message: str


class Outputs(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def _render_prompt(self, inputs: Inputs) -> dict[str, str]:
        if self.prompt_source is None:
            raise RuntimeError("intent_classifier: prompt.md missing")
        template = self.prompt_source.get_template()
        corpus = self.config.get("corpus_description", "")
        return render(template, {
            "message": inputs.message,
            "corpus_description": corpus,
        })

    def invoke(self, inputs_dict: dict[str, Any], *, model_override: str | None = None) -> dict[str, Any]:
        inputs = self._validate_inputs(inputs_dict)

        try:
            rendered = self._render_prompt(inputs)
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
            payload = _extract_json(output.answer_text or "")
            intent = payload.get("intent", "direct_answer")
            if intent not in _VALID_INTENTS:
                intent = "direct_answer"
            confidence = float(payload.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            reason = str(payload.get("reason", "model_classification"))
            return self._validate_outputs({
                "intent": intent,
                "confidence": confidence,
                "reason": reason,
            }).model_dump()
        except Exception as exc:
            return self._validate_outputs(self.fallback(inputs, exc)).model_dump()

    def fallback(self, inputs: Inputs, error: Exception) -> dict[str, Any]:
        lowered = inputs.message.lower()

        date_patterns = ["hôm nay là ngày", "hôm nay ngày mấy", "today's date", "what date is today"]
        if any(p in lowered for p in date_patterns):
            return {"intent": "current_date", "confidence": 0.9, "reason": "fallback_date_keyword"}

        web_keywords = [
            "hôm nay", "today", "hiện tại", "bây giờ", "mới nhất", "latest",
            "giá", "price", "thời tiết", "weather", "tin tức", "news",
            "sắp tới", "sắp diễn ra", "tuần tới", "tháng tới", "năm nay",
            "lễ hội", "festival", "sự kiện", "event", "upcoming",
        ]
        if any(k in lowered for k in web_keywords):
            return {"intent": "web_search", "confidence": 0.6, "reason": "fallback_temporal_keyword"}

        history_keywords = [
            "hùng vương", "an dương vương", "triệu đà", "đông sơn", "sa huỳnh",
            "óc eo", "hai bà trưng", "bà triệu", "bắc thuộc", "ngô quyền",
            "bạch đằng", "lý bí", "mai thúc loan", "phùng hưng", "khúc thừa dụ",
            "dương đình nghệ",
        ]
        if any(k in lowered for k in history_keywords):
            return {"intent": "local_rag", "confidence": 0.6, "reason": "fallback_corpus_keyword"}

        return {"intent": "direct_answer", "confidence": 0.5, "reason": "fallback_default"}
