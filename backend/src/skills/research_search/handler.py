from __future__ import annotations

import json
import os
from typing import Any, Callable

import httpx
from pydantic import BaseModel

from agent.models import ResearchResult, SearchResult
from skills._base import BaseSkill
from skills._errors import SkillValidationError
from skills._prompt_loader import render

try:
    from langsmith import traceable
except Exception:
    traceable = None


def _is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _langsmith_manual_tracing_enabled() -> bool:
    if traceable is None:
        return False
    if not os.getenv("LANGSMITH_API_KEY", "").strip():
        return False
    return _is_truthy_env("LANGSMITH_TRACING") or _is_truthy_env("LANGCHAIN_TRACING_V2")


class Inputs(BaseModel):
    task_order: int
    query: str
    goal: str


class Outputs(BaseModel):
    task_order: int
    extracted_information: str
    sources: list[str] = []
    success: bool = True
    error: str | None = None


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    # Injected at construction time from deps (Tavily key, custom executor)
    tavily_api_key: str | None = None
    search_executor: Callable[[str, int], list[dict[str, str]]] | None = None

    def __init__(self, *, tavily_api_key: str | None = None,
                 search_executor: Callable[[str, int], list[dict[str, str]]] | None = None,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self.tavily_api_key = tavily_api_key
        self.search_executor = search_executor

    def _max_results(self) -> int:
        return int(self.config.get("max_results", 3))

    def _call_tavily(self, query: str) -> dict:
        def _execute(*, traced_query: str, traced_max_results: int) -> dict:
            response = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": traced_query,
                    "max_results": traced_max_results,
                    "search_depth": "basic",
                    "include_answer": False,
                    "include_images": False,
                    "include_raw_content": False,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json() or {}

        if _langsmith_manual_tracing_enabled():
            traced_execute = traceable(name="tavily.search", run_type="tool")(_execute)
            return traced_execute(traced_query=query, traced_max_results=self._max_results())
        return _execute(traced_query=query, traced_max_results=self._max_results())

    def _search(self, query: str) -> list[SearchResult]:
        max_n = self._max_results()
        if self.search_executor is not None:
            rows = self.search_executor(query, max_n)
            return [
                SearchResult(
                    title=str(item.get("title", "")),
                    url=str(item.get("url", "")),
                    snippet=str(item.get("snippet", "")),
                )
                for item in rows[:max_n]
            ]

        if not self.tavily_api_key:
            return []

        try:
            payload = self._call_tavily(query)
            items = payload.get("results", [])
            return [
                SearchResult(
                    title=str(item.get("title", "")),
                    url=str(item.get("url", "")),
                    snippet=str(item.get("content", "")),
                )
                for item in items[:max_n]
            ]
        except Exception:
            return []

    def _extract_information(self, goal: str, results: list[SearchResult], model_override: str | None) -> str:
        if not results:
            return ""
        packed = [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results]

        try:
            template = self.prompt_source.get_template() if self.prompt_source else None
            if template is None:
                raise RuntimeError("research_search skill missing prompt.md")
            rendered = render(template, {"goal": goal, "search_results_json": json.dumps(packed, ensure_ascii=False)})
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
            return (output.answer_text or "").strip()
        except Exception:
            lines = [f"- {r.title}: {r.snippet}" for r in results if r.snippet]
            return "\n".join(lines[:3]).strip()

    def invoke(self, inputs_dict: dict[str, Any], *, model_override: str | None = None) -> dict[str, Any]:
        inputs = self._validate_inputs(inputs_dict)
        try:
            results = self._search(inputs.query)
            extracted = self._extract_information(inputs.goal, results, model_override)
            return self._validate_outputs(
                {
                    "task_order": inputs.task_order,
                    "extracted_information": extracted,
                    "sources": [r.url for r in results if r.url],
                    "success": True,
                    "error": None,
                }
            ).model_dump()
        except SkillValidationError:
            raise
        except Exception as exc:
            return self._validate_outputs(
                {
                    "task_order": inputs.task_order,
                    "extracted_information": "",
                    "sources": [],
                    "success": False,
                    "error": str(exc),
                }
            ).model_dump()


def to_research_result(skill_output: dict[str, Any]) -> ResearchResult:
    return ResearchResult(**skill_output)
