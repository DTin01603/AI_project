from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

from agent.models import ResearchTask
from skills._base import BaseSkill

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _extract_json_array(raw: str) -> list[dict[str, Any]]:
    stripped = (raw or "").strip()
    fence_match = _FENCE_RE.match(stripped)
    if fence_match:
        stripped = fence_match.group(1).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        arr_match = _ARRAY_RE.search(stripped)
        if not arr_match:
            raise
        data = json.loads(arr_match.group(0))
    if not isinstance(data, list):
        raise ValueError("invalid planning payload: not a list")
    return data


class Inputs(BaseModel):
    question: str


class TaskItem(BaseModel):
    order: int
    query: str
    goal: str


class Outputs(BaseModel):
    tasks: list[TaskItem]


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def parse_output(self, raw: str, inputs: Inputs) -> dict[str, Any]:
        data = _extract_json_array(raw)
        tasks: list[dict[str, Any]] = []
        for item in data:
            tasks.append(
                {
                    "order": int(item.get("order", len(tasks) + 1)),
                    "query": str(item.get("query", "")).strip(),
                    "goal": (str(item.get("goal", "")).strip() or "Nghiên cứu"),
                }
            )
        tasks = [t for t in tasks if t["query"]]
        tasks.sort(key=lambda t: t["order"])
        if not tasks:
            raise ValueError("empty plan after sanitize")
        return {"tasks": tasks[:5]}

    def fallback(self, inputs: Inputs, error: Exception) -> dict[str, Any]:
        q = inputs.question
        return {
            "tasks": [
                {"order": 1, "query": q, "goal": "Thu thập thông tin chính"},
                {"order": 2, "query": f"Số liệu mới nhất về: {q}", "goal": "Lấy dữ liệu cập nhật"},
                {"order": 3, "query": f"Tổng hợp và so sánh: {q}", "goal": "Rút ra kết luận"},
            ]
        }


def to_research_tasks(skill_output: dict[str, Any]) -> list[ResearchTask]:
    """Convert skill output dict to list[ResearchTask] for LangGraph state."""
    return [ResearchTask(**t) for t in skill_output["tasks"]]
