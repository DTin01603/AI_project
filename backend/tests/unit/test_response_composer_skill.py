from __future__ import annotations

from pathlib import Path

from adapters.base import AdapterOutput
from skills import SkillRegistry

_SKILLS_ROOT = Path(__file__).resolve().parents[2] / "src" / "skills"


class _StubAdapter:
    provider = "stub"

    def __init__(self, output_text: str = "", raise_exc: Exception | None = None):
        self._text = output_text
        self._raise = raise_exc

    def invoke(self, *, model, messages, constraints):
        if self._raise is not None:
            raise self._raise
        return AdapterOutput(answer_text=self._text)


def _load_skill(adapter):
    reg = SkillRegistry()
    reg.discover(_SKILLS_ROOT)
    skill = reg.get("response_composer")
    skill._adapter_factory = lambda m: adapter
    skill._adapter_cache.clear()
    return skill


def test_returns_llm_answer_when_successful() -> None:
    skill = _load_skill(_StubAdapter("Đây là câu trả lời tổng hợp."))
    out = skill.invoke({"question": "Hà Nội có gì?", "knowledge_base": "Hà Nội là thủ đô."})
    assert out["answer"] == "Đây là câu trả lời tổng hợp."


def test_short_circuit_empty_knowledge_base() -> None:
    skill = _load_skill(_StubAdapter("should not be called"))
    out = skill.invoke({"question": "X?", "knowledge_base": "   "})
    assert "chưa thu thập đủ" in out["answer"]


def test_fallback_returns_knowledge_base_on_adapter_error() -> None:
    skill = _load_skill(_StubAdapter(raise_exc=RuntimeError("api down")))
    kb = "Dữ liệu thô từ pipeline."
    out = skill.invoke({"question": "Q?", "knowledge_base": kb})
    assert out["answer"] == kb


def test_empty_llm_response_falls_back_to_knowledge_base() -> None:
    skill = _load_skill(_StubAdapter("   "))
    kb = "Only raw KB"
    out = skill.invoke({"question": "Q?", "knowledge_base": kb})
    assert out["answer"] == kb
