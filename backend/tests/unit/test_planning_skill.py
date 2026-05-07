from __future__ import annotations

from pathlib import Path

from adapters.base import AdapterOutput
from skills import SkillRegistry

_SKILLS_ROOT = Path(__file__).resolve().parents[2] / "src" / "skills"


class _StubAdapter:
    provider = "stub"

    def __init__(self, output_text: str = "[]", raise_exc: Exception | None = None):
        self._text = output_text
        self._raise = raise_exc

    def invoke(self, *, model, messages, constraints):
        if self._raise is not None:
            raise self._raise
        return AdapterOutput(answer_text=self._text)


def _load_skill(adapter):
    reg = SkillRegistry()
    reg.discover(_SKILLS_ROOT)
    skill = reg.get("planning")
    skill._adapter_factory = lambda m: adapter
    skill._adapter_cache.clear()
    return skill


def test_parses_valid_plan() -> None:
    raw = '[{"order":1,"query":"q1","goal":"g1"},{"order":2,"query":"q2","goal":"g2"}]'
    skill = _load_skill(_StubAdapter(raw))
    out = skill.invoke({"question": "Nghiên cứu AI 2026"})
    assert len(out["tasks"]) == 2
    assert out["tasks"][0]["order"] == 1
    assert out["tasks"][1]["query"] == "q2"


def test_caps_plan_at_5_tasks() -> None:
    items = [{"order": i, "query": f"q{i}", "goal": f"g{i}"} for i in range(1, 11)]
    import json as _json

    raw = _json.dumps(items)
    skill = _load_skill(_StubAdapter(raw))
    out = skill.invoke({"question": "Q"})
    assert len(out["tasks"]) == 5


def test_parses_markdown_fenced_plan() -> None:
    raw = '```json\n[{"order":1,"query":"a","goal":"b"}]\n```'
    skill = _load_skill(_StubAdapter(raw))
    out = skill.invoke({"question": "Q"})
    assert out["tasks"][0]["query"] == "a"


def test_fallback_on_invalid_json() -> None:
    skill = _load_skill(_StubAdapter("not a valid array"))
    out = skill.invoke({"question": "Giá vàng"})
    assert len(out["tasks"]) == 3
    assert "Giá vàng" in out["tasks"][0]["query"]


def test_fallback_on_empty_plan() -> None:
    skill = _load_skill(_StubAdapter("[]"))
    out = skill.invoke({"question": "Q"})
    assert len(out["tasks"]) == 3  # fallback triggered


def test_fallback_on_adapter_error() -> None:
    skill = _load_skill(_StubAdapter(raise_exc=RuntimeError("api down")))
    out = skill.invoke({"question": "Q"})
    assert len(out["tasks"]) == 3


def test_skips_empty_queries() -> None:
    raw = '[{"order":1,"query":"","goal":"g"},{"order":2,"query":"real","goal":"g2"}]'
    skill = _load_skill(_StubAdapter(raw))
    out = skill.invoke({"question": "Q"})
    assert len(out["tasks"]) == 1
    assert out["tasks"][0]["query"] == "real"


def test_to_research_tasks_helper() -> None:
    from skills.planning.handler import to_research_tasks

    skill_out = {"tasks": [{"order": 1, "query": "q", "goal": "g"}]}
    rts = to_research_tasks(skill_out)
    assert rts[0].query == "q"
    assert rts[0].order == 1
