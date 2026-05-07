from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from adapters.base import AdapterOutput
from skills import (
    BaseSkill,
    SkillNotFoundError,
    SkillRegistry,
    SkillValidationError,
)


class _StubAdapter:
    provider = "stub"

    def __init__(self, output_text: str = '{"ok": true}', raise_exc: Exception | None = None) -> None:
        self._text = output_text
        self._raise = raise_exc
        self.calls: list[dict[str, Any]] = []

    def invoke(self, *, model: str, messages: list, constraints: dict):
        self.calls.append({"model": model, "messages": messages, "constraints": constraints})
        if self._raise is not None:
            raise self._raise
        return AdapterOutput(answer_text=self._text)


class _EchoInputs(BaseModel):
    text: str


class _EchoOutputs(BaseModel):
    echoed: str


def _make_skill(tmp_path: Path, *, prompt_body: str = "{% block user %}Say: {{ text }}{% endblock %}",
                llm: bool = True, adapter=None) -> BaseSkill:
    folder = tmp_path / "echo_skill"
    folder.mkdir()
    (folder / "skill.yaml").write_text(
        f"name: echo_skill\nversion: 1\nmodel: stub/dummy\ntemperature: 0.0\nmax_output_tokens: 32\nllm: {str(llm).lower()}\n",
        encoding="utf-8",
    )
    if llm:
        (folder / "prompt.md").write_text(prompt_body, encoding="utf-8")

    handler_code = '''
from pydantic import BaseModel
from skills import BaseSkill


class Inputs(BaseModel):
    text: str


class Outputs(BaseModel):
    echoed: str


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def parse_output(self, raw, inputs):
        return {"echoed": raw.strip()}

    def fallback(self, inputs, error):
        return {"echoed": f"fallback:{inputs.text}"}

    def run(self, inputs):
        return {"echoed": f"pure:{inputs.text}"}
'''
    (folder / "handler.py").write_text(handler_code, encoding="utf-8")

    reg = SkillRegistry()
    reg.discover(tmp_path)
    skill = reg.get("echo_skill")
    if adapter is not None:
        skill._adapter_factory = lambda model: adapter
        skill._adapter_cache.clear()
    return skill


def test_registry_discovers_skill(tmp_path: Path) -> None:
    skill = _make_skill(tmp_path, adapter=_StubAdapter('hello world'))
    assert skill.name == "echo_skill"
    assert skill.version == "1"
    assert skill.model == "stub/dummy"


def test_registry_get_missing_raises(tmp_path: Path) -> None:
    reg = SkillRegistry()
    reg.discover(tmp_path)  # empty dir
    with pytest.raises(SkillNotFoundError):
        reg.get("does_not_exist")


def test_invoke_validates_inputs(tmp_path: Path) -> None:
    skill = _make_skill(tmp_path, adapter=_StubAdapter('x'))
    with pytest.raises(SkillValidationError):
        skill.invoke({})  # missing 'text'


def test_invoke_happy_path(tmp_path: Path) -> None:
    adapter = _StubAdapter("hello")
    skill = _make_skill(tmp_path, adapter=adapter)
    out = skill.invoke({"text": "abc"})
    assert out == {"echoed": "hello"}
    assert adapter.calls[0]["model"] == "stub/dummy"
    assert adapter.calls[0]["messages"] == [("user", "Say: abc")]


def test_invoke_fallback_on_adapter_exception(tmp_path: Path) -> None:
    adapter = _StubAdapter(raise_exc=RuntimeError("boom"))
    skill = _make_skill(tmp_path, adapter=adapter)
    out = skill.invoke({"text": "abc"})
    assert out == {"echoed": "fallback:abc"}


def test_validates_outputs(tmp_path: Path) -> None:
    folder = tmp_path / "bad_output"
    folder.mkdir()
    (folder / "skill.yaml").write_text(
        "name: bad_output\nversion: 1\nmodel: stub/dummy\nllm: true\n", encoding="utf-8",
    )
    (folder / "prompt.md").write_text("{% block user %}x{% endblock %}", encoding="utf-8")
    (folder / "handler.py").write_text(
        '''
from pydantic import BaseModel
from skills import BaseSkill


class Inputs(BaseModel):
    text: str


class Outputs(BaseModel):
    required_field: str


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def parse_output(self, raw, inputs):
        return {"wrong_key": "oops"}
''',
        encoding="utf-8",
    )
    reg = SkillRegistry()
    reg.discover(tmp_path)
    skill = reg.get("bad_output")
    skill._adapter_factory = lambda m: _StubAdapter("x")
    skill._adapter_cache.clear()
    with pytest.raises(SkillValidationError):
        skill.invoke({"text": "hi"})


def test_non_llm_skill_uses_run(tmp_path: Path) -> None:
    skill = _make_skill(tmp_path, llm=False)
    out = skill.invoke({"text": "abc"})
    assert out == {"echoed": "pure:abc"}


def test_model_override(tmp_path: Path) -> None:
    adapter = _StubAdapter("ok")
    skill = _make_skill(tmp_path, adapter=adapter)
    skill.invoke({"text": "x"}, model_override="gemini-custom")
    assert adapter.calls[0]["model"] == "gemini-custom"


def test_jinja_strict_undefined_raises_on_missing_var(tmp_path: Path) -> None:
    skill = _make_skill(
        tmp_path,
        prompt_body="{% block user %}{{ missing_var }}{% endblock %}",
        adapter=_StubAdapter('x'),
    )
    # missing_var not provided -> Jinja StrictUndefined -> invocation error -> fallback
    out = skill.invoke({"text": "hello"})
    assert out["echoed"].startswith("fallback:")


def test_model_falls_back_to_settings_default_when_yaml_omits_it(tmp_path: Path) -> None:
    """skill.yaml without `model:` → uses settings.default_model as default."""
    folder = tmp_path / "no_model_skill"
    folder.mkdir()
    (folder / "skill.yaml").write_text(
        "name: no_model_skill\nversion: 1\nllm: true\ntemperature: 0.0\n", encoding="utf-8",
    )
    (folder / "prompt.md").write_text("{% block user %}x{% endblock %}", encoding="utf-8")
    (folder / "handler.py").write_text(
        '''
from pydantic import BaseModel
from skills import BaseSkill


class Inputs(BaseModel):
    text: str


class Outputs(BaseModel):
    ok: bool


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def parse_output(self, raw, inputs):
        return {"ok": True}
''',
        encoding="utf-8",
    )
    reg = SkillRegistry()
    reg.discover(tmp_path)
    skill = reg.get("no_model_skill")

    from config import settings
    assert skill.model == settings.default_model  # fell through to settings

    adapter = _StubAdapter("x")
    skill._adapter_factory = lambda m: adapter
    skill._adapter_cache.clear()
    skill.invoke({"text": "hi"})
    assert adapter.calls[0]["model"] == settings.default_model


def test_prompt_auto_reload_on_mtime_change(tmp_path: Path) -> None:
    import os

    folder = tmp_path / "echo_skill"
    folder.mkdir()
    (folder / "skill.yaml").write_text(
        "name: echo_skill\nversion: 1\nmodel: stub/dummy\nllm: true\n", encoding="utf-8",
    )
    prompt_path = folder / "prompt.md"
    prompt_path.write_text("{% block user %}V1:{{ text }}{% endblock %}", encoding="utf-8")
    (folder / "handler.py").write_text(
        '''
from pydantic import BaseModel
from skills import BaseSkill


class Inputs(BaseModel):
    text: str


class Outputs(BaseModel):
    echoed: str


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def parse_output(self, raw, inputs):
        return {"echoed": raw.strip()}
''',
        encoding="utf-8",
    )

    reg = SkillRegistry()
    reg.discover(tmp_path)
    skill = reg.get("echo_skill")
    captured_prompts: list[str] = []

    def _record_adapter(model):
        class _A:
            provider = "stub"

            def invoke(self, *, model, messages, constraints):
                captured_prompts.append(messages[-1][1])
                return AdapterOutput(answer_text="ok")

        return _A()

    skill._adapter_factory = _record_adapter
    skill._adapter_cache.clear()

    skill.invoke({"text": "foo"})
    assert captured_prompts[-1] == "V1:foo"

    # Rewrite prompt with bumped mtime
    prompt_path.write_text("{% block user %}V2:{{ text }}{% endblock %}", encoding="utf-8")
    new_mtime = prompt_path.stat().st_mtime + 1.0
    os.utime(prompt_path, (new_mtime, new_mtime))

    skill.invoke({"text": "bar"})
    assert captured_prompts[-1] == "V2:bar"


def test_skill_yaml_with_system_and_user_blocks(tmp_path: Path) -> None:
    folder = tmp_path / "multi_block"
    folder.mkdir()
    (folder / "skill.yaml").write_text(
        "name: multi_block\nversion: 1\nmodel: stub/dummy\nllm: true\n", encoding="utf-8",
    )
    (folder / "prompt.md").write_text(
        "{% block system %}SYS{% endblock %}\n{% block user %}USER:{{ text }}{% endblock %}",
        encoding="utf-8",
    )
    (folder / "handler.py").write_text(
        '''
from pydantic import BaseModel
from skills import BaseSkill


class Inputs(BaseModel):
    text: str


class Outputs(BaseModel):
    ok: bool


class Handler(BaseSkill):
    Inputs = Inputs
    Outputs = Outputs

    def parse_output(self, raw, inputs):
        return {"ok": True}
''',
        encoding="utf-8",
    )
    reg = SkillRegistry()
    reg.discover(tmp_path)
    skill = reg.get("multi_block")
    adapter = _StubAdapter("x")
    skill._adapter_factory = lambda m: adapter
    skill._adapter_cache.clear()
    skill.invoke({"text": "hi"})
    assert adapter.calls[0]["messages"] == [("system", "SYS"), ("user", "USER:hi")]
