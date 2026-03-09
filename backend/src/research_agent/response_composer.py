from __future__ import annotations

from adapters import get_adapter_for_model
from adapters.base import BaseAdapter


class ResponseComposer:
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        timeout_seconds: float = 15.0,
        adapter: BaseAdapter | None = None,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.adapter = adapter or get_adapter_for_model(model)

    @staticmethod
    def _build_composition_prompt(question: str, knowledge_base: str) -> str:
        # Prompt template for composing final user-facing answer from evidence.
        return (
            "Compose a clear final answer for the user question based only on the given knowledge base. "
            "If data is incomplete, mention uncertainty briefly. Use Vietnamese when appropriate.\n"
            f"Question: {question}\n"
            f"KnowledgeBase:\n{knowledge_base}"
        )

    def compose(self, question: str, knowledge_base: str) -> str:
        # Compose final answer; fallback to raw knowledge base when composition fails.
        if not knowledge_base.strip():
            return "Mình chưa thu thập đủ dữ liệu để trả lời chắc chắn."

        prompt = self._build_composition_prompt(question, knowledge_base)
        try:
            output = self.adapter.invoke(
                model=self.model,
                messages=[("user", prompt)],
                constraints={"temperature": 0.2, "max_output_tokens": 1200},
            )
            answer = (output.answer_text or "").strip()
            if answer:
                return answer
        except Exception:
            pass
        return knowledge_base

    def gjcompose(self, question: str, knowledge_base: str) -> str:
        return self.compose(question, knowledge_base)
