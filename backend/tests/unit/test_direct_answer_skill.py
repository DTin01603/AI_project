from __future__ import annotations

from pathlib import Path

from adapters.base import AdapterOutput
from skills import SkillRegistry

_SKILLS_ROOT = Path(__file__).resolve().parents[2] / "src" / "skills"


class _RecordingAdapter:
    provider = "stub"

    def __init__(self, output_text: str = "Xin chào!", raise_on_call: Exception | None = None):
        self._text = output_text
        self._raise = raise_on_call
        self.calls: list[dict] = []

    def invoke(self, *, model, messages, constraints):
        self.calls.append({"model": model, "messages": messages, "constraints": constraints})
        if self._raise is not None:
            raise self._raise
        return AdapterOutput(answer_text=self._text, finish_reason="stop")


def _load_skill(adapter):
    reg = SkillRegistry()
    reg.discover(_SKILLS_ROOT)
    skill = reg.get("direct_answer")
    skill._adapter_factory = lambda m: adapter
    skill._adapter_cache.clear()
    return skill


def test_basic_answer_no_history() -> None:
    adapter = _RecordingAdapter("Chào bạn, tôi có thể giúp gì?")
    skill = _load_skill(adapter)
    out = skill.invoke({"user_message": "Xin chào", "history": []})
    assert out["answer"] == "Chào bạn, tôi có thể giúp gì?"
    assert out["finish_reason"] == "stop"
    # Messages should have: system + user (no history)
    msgs = adapter.calls[0]["messages"]
    assert msgs[0][0] == "system"
    assert "trợ lý AI" in msgs[0][1]
    assert msgs[-1] == ("user", "Xin chào")


def test_history_is_included() -> None:
    adapter = _RecordingAdapter("ok")
    skill = _load_skill(adapter)
    history = [
        {"role": "user", "content": "Câu 1"},
        {"role": "assistant", "content": "Trả lời 1"},
    ]
    skill.invoke({"user_message": "Câu 2", "history": history})
    msgs = adapter.calls[0]["messages"]
    # system + 2 history + current user
    assert len(msgs) == 4
    assert msgs[1] == ("user", "Câu 1")
    assert msgs[2] == ("assistant", "Trả lời 1")
    assert msgs[3] == ("user", "Câu 2")


def test_history_trims_to_max_messages() -> None:
    adapter = _RecordingAdapter("ok")
    skill = _load_skill(adapter)
    skill.config["max_history_messages"] = 4
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(20)]
    skill.invoke({"user_message": "now", "history": history})
    msgs = adapter.calls[0]["messages"]
    # system + 4 history + current = 6
    assert len(msgs) == 6


def test_history_skips_invalid_role() -> None:
    adapter = _RecordingAdapter("ok")
    skill = _load_skill(adapter)
    history = [
        {"role": "system", "content": "should be skipped"},
        {"role": "user", "content": "real user turn"},
    ]
    skill.invoke({"user_message": "now", "history": history})
    msgs = adapter.calls[0]["messages"]
    # system + 1 valid history + current
    assert len(msgs) == 3
    assert msgs[1] == ("user", "real user turn")


def test_trims_long_user_message() -> None:
    adapter = _RecordingAdapter("ok")
    skill = _load_skill(adapter)
    skill.config["max_turn_chars"] = 50
    long_msg = "x" * 200
    skill.invoke({"user_message": long_msg, "history": []})
    msgs = adapter.calls[0]["messages"]
    assert len(msgs[-1][1]) == 50


def test_fallback_when_empty_output_after_retries() -> None:
    adapter = _RecordingAdapter(output_text="")
    skill = _load_skill(adapter)
    skill.config["max_retries"] = 0  # no retry, fail fast
    out = skill.invoke({"user_message": "hi", "history": []})
    assert "Xin lỗi" in out["answer"]
    assert out["finish_reason"] == "error"


def test_fallback_on_exception() -> None:
    adapter = _RecordingAdapter(raise_on_call=RuntimeError("api down"))
    skill = _load_skill(adapter)
    skill.config["max_retries"] = 0
    out = skill.invoke({"user_message": "hi", "history": []})
    assert out["finish_reason"] == "error"
    assert out["provider"] is None
