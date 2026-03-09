from __future__ import annotations

import json

from adapters import get_adapter_for_model
from adapters.base import BaseAdapter
from research_agent.models import ResearchTask


class PlanningAgent:
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        timeout_seconds: float = 5.0,
        adapter: BaseAdapter | None = None,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.adapter = adapter or get_adapter_for_model(model)

    @staticmethod
    def _build_planning_prompt(question: str) -> str:
        # Prompt template to generate structured multi-step research plan.
        return (
            "Create a concise research plan in JSON array format only. "
            "Each item must have keys: order (int), query (string), goal (string). "
            "Plan size must be between 1 and 5 tasks. "
            f"Question: {question}"
        )

    @staticmethod
    def _fallback_plan(question: str) -> list[ResearchTask]:
        # Deterministic backup plan when model output is invalid/unavailable.
        return [
            ResearchTask(order=1, query=question, goal="Thu thập thông tin chính"),
            ResearchTask(order=2, query=f"Số liệu mới nhất về: {question}", goal="Lấy dữ liệu cập nhật"),
            ResearchTask(order=3, query=f"Tổng hợp và so sánh: {question}", goal="Rút ra kết luận"),
        ]

    def create_plan(self, question: str) -> list[ResearchTask]:
        # Create and sanitize ordered research tasks (max 5).
        prompt = self._build_planning_prompt(question)
        try:
            output = self.adapter.invoke(
                model=self.model,
                messages=[("user", prompt)],
                constraints={"temperature": 0.1, "max_output_tokens": 700},
            )
            data = json.loads((output.answer_text or "").strip())
            if not isinstance(data, list):
                raise ValueError("invalid planning payload")

            tasks: list[ResearchTask] = []
            for item in data:
                tasks.append(
                    ResearchTask(
                        order=int(item.get("order", len(tasks) + 1)),
                        query=str(item.get("query", "")).strip(),
                        goal=str(item.get("goal", "")).strip() or "Nghiên cứu",
                    )
                )

            tasks = [task for task in tasks if task.query]
            tasks.sort(key=lambda task: task.order)
            if not tasks:
                raise ValueError("empty plan")

            return tasks[:5]
        except Exception:
            return self._fallback_plan(question)
