from __future__ import annotations

import json
import os
from typing import Callable

import httpx

from adapters import get_adapter_for_model
from adapters.base import BaseAdapter
from research_agent.models import ResearchResult, SearchResult

try:
    from langsmith import traceable
except Exception:  # pragma: no cover - optional dependency at runtime
    traceable = None


def _is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _langsmith_manual_tracing_enabled() -> bool:
    if traceable is None:
        return False
    if not os.getenv("LANGSMITH_API_KEY", "").strip():
        return False
    return _is_truthy_env("LANGSMITH_TRACING") or _is_truthy_env("LANGCHAIN_TRACING_V2")


class ResearchTool:
    def __init__(
        self,
        tavily_api_key: str | None,
        llm_api_key: str | None,
        model: str = "gemini-2.5-flash",
        max_results: int = 3,
        search_executor: Callable[[str, int], list[dict[str, str]]] | None = None,
        adapter: BaseAdapter | None = None,
    ) -> None:
        self.tavily_api_key = tavily_api_key
        self.llm_api_key = llm_api_key
        self.model = model
        self.max_results = max_results
        self.search_executor = search_executor
        self.adapter = adapter or get_adapter_for_model(model)

    def _call_tavily(self, query: str) -> dict:
        """Call Tavily search API and optionally emit a LangSmith tool span."""

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
            return traced_execute(
                traced_query=query,
                traced_max_results=self.max_results,
            )

        return _execute(
            traced_query=query,
            traced_max_results=self.max_results,
        )

    def _search(self, query: str) -> list[SearchResult]:
        # Execute web search (custom executor or Tavily) and normalize results.
        if self.search_executor is not None:
            rows = self.search_executor(query, self.max_results)
            return [
                SearchResult(
                    title=str(item.get("title", "")),
                    url=str(item.get("url", "")),
                    snippet=str(item.get("snippet", "")),
                )
                for item in rows[: self.max_results]
            ]

        if not self.tavily_api_key:
            return []

        try:
            payload = self._call_tavily(query)
            items = payload.get("results", [])
            results: list[SearchResult] = []
            for item in items[: self.max_results]:
                results.append(
                    SearchResult(
                        title=str(item.get("title", "")),
                        url=str(item.get("url", "")),
                        snippet=str(item.get("content", "")),
                    )
                )
            return results
        except Exception:
            return []

    def _extract_information(self, goal: str, search_results: list[SearchResult]) -> str:
        # Extract concise evidence from search results using LLM, with text fallback.
        if not search_results:
            return ""

        packed_results = [
            {
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
            }
            for result in search_results
        ]
        prompt = (
            "Extract concise, relevant information for the goal from search results. "
            "Use Vietnamese if goal is Vietnamese. Return plain text only.\n"
            f"Goal: {goal}\n"
            f"SearchResults(JSON): {json.dumps(packed_results, ensure_ascii=False)}"
        )

        try:
            output = self.adapter.invoke(
                model=self.model,
                messages=[("user", prompt)],
                constraints={"temperature": 0.2, "max_output_tokens": 900},
            )
            return (output.answer_text or "").strip()
        except Exception:
            lines = [f"- {item.title}: {item.snippet}" for item in search_results if item.snippet]
            return "\n".join(lines[:3]).strip()

    def execute_task(self, task_order: int, query: str, goal: str) -> ResearchResult:
        # Run one research task end-to-end: search -> extract -> package structured result.
        try:
            search_results = self._search(query)
            extracted = self._extract_information(goal, search_results)
            return ResearchResult(
                task_order=task_order,
                extracted_information=extracted,
                sources=[item.url for item in search_results if item.url],
                success=True,
                error=None,
            )
        except Exception as error:
            return ResearchResult(
                task_order=task_order,
                extracted_information="",
                sources=[],
                success=False,
                error=str(error),
            )
