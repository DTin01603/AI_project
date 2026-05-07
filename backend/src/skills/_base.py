from __future__ import annotations

import logging
import time
from abc import ABC
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

from adapters import get_adapter_for_model
from adapters.base import AdapterOutput, BaseAdapter
from config import settings
from skills._errors import SkillInvocationError, SkillValidationError
from skills._prompt_loader import PromptSource, render

logger = logging.getLogger("skills")


class BaseSkill(ABC):
    """Base class for all skills. Subclass and set Inputs/Outputs,
    optionally override parse_output() and fallback()."""

    Inputs: ClassVar[type[BaseModel]] = BaseModel
    Outputs: ClassVar[type[BaseModel]] = BaseModel

    def __init__(
        self,
        *,
        name: str,
        version: str | int = 1,
        config: dict[str, Any] | None = None,
        prompt_source: PromptSource | None = None,
        adapter_factory=get_adapter_for_model,
    ) -> None:
        self.name = name
        self.version = str(version)
        self.config = config or {}
        self.prompt_source = prompt_source
        # model resolution: skill.yaml > settings.default_model (env DEFAULT_MODEL)
        self.model: str | None = self.config.get("model") or getattr(settings, "default_model", None)
        self.temperature: float = float(self.config.get("temperature", 0.0))
        self.max_output_tokens: int = int(self.config.get("max_output_tokens", 512))
        self.uses_llm: bool = bool(self.config.get("llm", True))
        self._adapter_factory = adapter_factory
        self._adapter_cache: dict[str, BaseAdapter] = {}

    def invoke(self, inputs_dict: dict[str, Any], *, model_override: str | None = None) -> dict[str, Any]:
        inputs = self._validate_inputs(inputs_dict)
        start = time.perf_counter()
        fallback_used = False

        try:
            if self.uses_llm:
                raw = self._call_llm(inputs, model_override=model_override)
                outputs_dict = self.parse_output(raw, inputs)
            else:
                outputs_dict = self.run(inputs)
        except SkillValidationError:
            raise
        except Exception as exc:
            logger.warning("[SKILL] name=%s fallback triggered: %s", self.name, exc)
            fallback_used = True
            try:
                outputs_dict = self.fallback(inputs, exc)
            except Exception as fb_exc:
                raise SkillInvocationError(f"skill {self.name} failed and fallback raised: {fb_exc}") from fb_exc

        outputs = self._validate_outputs(outputs_dict)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[SKILL] name=%s duration_ms=%.2f fallback=%s",
            self.name,
            duration_ms,
            fallback_used,
        )
        return outputs.model_dump()

    def parse_output(self, raw: str, inputs: BaseModel) -> dict[str, Any]:
        """Override for LLM skills to parse raw text into output dict."""
        return {"text": raw}

    def fallback(self, inputs: BaseModel, error: Exception) -> dict[str, Any]:
        """Override to provide graceful degradation on failure."""
        raise error

    def run(self, inputs: BaseModel) -> dict[str, Any]:
        """Override for non-LLM skills (llm: false in skill.yaml)."""
        raise NotImplementedError(f"skill {self.name} has llm: false but does not implement run()")

    def _validate_inputs(self, inputs_dict: dict[str, Any]) -> BaseModel:
        try:
            return self.Inputs(**inputs_dict)
        except ValidationError as exc:
            raise SkillValidationError(f"skill {self.name} inputs invalid: {exc}") from exc

    def _validate_outputs(self, outputs_dict: dict[str, Any]) -> BaseModel:
        try:
            return self.Outputs(**outputs_dict)
        except ValidationError as exc:
            raise SkillValidationError(f"skill {self.name} outputs invalid: {exc}") from exc

    def _call_llm(self, inputs: BaseModel, *, model_override: str | None = None) -> str:
        if self.prompt_source is None:
            raise SkillInvocationError(f"skill {self.name} missing prompt.md but uses_llm=True")

        model = model_override or self.model
        if not model:
            raise SkillInvocationError(f"skill {self.name} has no model configured")

        context = inputs.model_dump()
        template = self.prompt_source.get_template()
        prompt = render(template, context)

        messages: list[tuple[str, str]] = []
        if "system" in prompt:
            messages.append(("system", prompt["system"]))
        messages.append(("user", prompt["user"]))

        adapter = self._resolve_adapter(model)
        constraints = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
        }
        output: AdapterOutput = adapter.invoke(
            model=model,
            messages=messages,
            constraints=constraints,
        )
        return output.answer_text

    def _resolve_adapter(self, model: str) -> BaseAdapter:
        if model not in self._adapter_cache:
            self._adapter_cache[model] = self._adapter_factory(model)
        return self._adapter_cache[model]

    def __repr__(self) -> str:
        return f"<Skill name={self.name} version={self.version} llm={self.uses_llm}>"
