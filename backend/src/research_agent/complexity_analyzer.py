import json
from dataclasses import dataclass

from adapters import get_adapter_for_model
from adapters.base import BaseAdapter


@dataclass
class ComplexityResult:
    is_complex: bool
    confidence: float
    reason: str


class ComplexityAnalyzer:
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        timeout_seconds: float = 2.0,
        adapter: BaseAdapter | None = None,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.adapter = adapter or get_adapter_for_model(model)

    @staticmethod
    def _build_analysis_prompt(message: str) -> str:
        # Prompt template for routing classifier: decide simple vs complex.
        return (
            "Classify user request complexity for routing. "
            "Return strict JSON with keys: is_complex (boolean), confidence (0..1), reason (string). "
            "Mark is_complex=true only if request needs multi-step research or external web evidence. "
            f"User request: {message}"
        )

    @staticmethod
    def _heuristic(message: str) -> ComplexityResult:
        # Fallback classification when model call fails.
        lowered = message.lower()
        complex_keywords = [
            "nghiên cứu",
            "research",
            "so sánh",
            "phân tích sâu",
            "nguồn",
            "citation",
            "market",
            "trend",
        ]
        is_complex = len(message) > 220 or any(token in lowered for token in complex_keywords)
        if is_complex:
            return ComplexityResult(is_complex=True, confidence=0.7, reason="heuristic_complex")
        return ComplexityResult(is_complex=False, confidence=0.8, reason="heuristic_simple")

    def analyze(self, message: str) -> ComplexityResult:
        # Primary path: ask LLM for JSON classification, then parse to ComplexityResult.
        prompt = self._build_analysis_prompt(message)
        try:
            output = self.adapter.invoke(
                model=self.model,
                messages=[("user", prompt)],
                constraints={"temperature": 0.0, "max_output_tokens": 150},
            )
            payload = json.loads(output.answer_text)
            return ComplexityResult(
                is_complex=bool(payload.get("is_complex", False)),
                confidence=float(payload.get("confidence", 0.5)),
                reason=str(payload.get("reason", "model_classification")),
            )
        except Exception:
            return self._heuristic(message)
