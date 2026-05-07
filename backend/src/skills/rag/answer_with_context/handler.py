from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from agent.utils import deduplicate_list, truncate
from skills._base import BaseSkill
from skills._errors import SkillValidationError
from skills._prompt_loader import render

logger = logging.getLogger(__name__)


class Inputs(BaseModel):
    question: str
    history: list[dict[str, str]] = []
    relevant_documents: list[dict[str, Any]] = []


class Outputs(BaseModel):
    generation: str
    citations: list[str] = []


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def _build_context(self, docs: list[dict[str, Any]]) -> tuple[str, list[str]]:
        max_docs = int(self.config.get("max_context_docs", 8))
        snippet_max = int(self.config.get("snippet_max_chars", 800))
        citations: list[str] = []
        blocks: list[str] = []
        for idx, doc in enumerate(docs[:max_docs], start=1):
            meta = doc.get("metadata") or {}
            source = str(meta.get("file_path") or meta.get("file_name") or doc.get("id", ""))
            snippet = truncate(doc.get("content", "").strip(), snippet_max)
            blocks.append(f"[{idx}] {source}\n{snippet}")
            if source:
                citations.append(source)
        return "\n\n".join(blocks), citations

    def _select_history(self, history: list[dict[str, str]]) -> list[tuple[str, str]]:
        selected: list[tuple[str, str]] = []
        for item in history[-12:]:  # last 12 turns
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                selected.append((role, content))
        return selected

    def invoke(self, inputs_dict: dict[str, Any], *, model_override: str | None = None) -> dict[str, Any]:
        inputs = self._validate_inputs(inputs_dict)

        try:
            context_text, citations = self._build_context(inputs.relevant_documents)
            augmented_question = inputs.question
            if context_text:
                augmented_question = (
                    "Bạn được cung cấp ngữ cảnh từ tài liệu nội bộ. "
                    "Ưu tiên trả lời dựa trên các đoạn này.\n\n"
                    "=== NGỮ CẢNH NỘI BỘ ===\n"
                    f"{context_text}\n\n"
                    "=== CÂU HỎI NGƯỜI DÙNG ===\n"
                    f"{inputs.question}"
                )

            template = self.prompt_source.get_template() if self.prompt_source else None
            if template is None:
                raise RuntimeError("answer_with_context: prompt.md missing")
            rendered = render(template, {"augmented_question": augmented_question})

            messages: list[tuple[str, str]] = []
            if "system" in rendered and rendered["system"]:
                messages.append(("system", rendered["system"]))
            messages.extend(self._select_history(inputs.history))
            messages.append(("user", rendered["user"]))

            model = model_override or self.model
            if not model:
                raise RuntimeError("no model configured")
            adapter = self._resolve_adapter(model)
            output = adapter.invoke(
                model=model,
                messages=messages,
                constraints={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_output_tokens,
                },
            )
            generation = (output.answer_text or "").strip()
            return self._validate_outputs({
                "generation": generation,
                "citations": deduplicate_list(citations),
            }).model_dump()

        except SkillValidationError:
            raise
        except Exception:
            logger.exception("answer_with_context invoke failed")
            return self._validate_outputs({
                "generation": "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời.",
                "citations": [],
            }).model_dump()
