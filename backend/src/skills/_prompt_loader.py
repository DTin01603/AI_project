from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined, Template, meta

from skills._errors import SkillInvocationError, SkillLoadError

_ENV = Environment(
    undefined=StrictUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=False,
)


class PromptSource:
    """Tracks a prompt.md file on disk and auto-reloads the Jinja2 template
    when the file's mtime changes. Cheap: one stat() call per invocation."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._mtime: float = -1.0
        self._template: Template | None = None

    def get_template(self) -> Template:
        try:
            current_mtime = self.path.stat().st_mtime
        except OSError as exc:
            raise SkillLoadError(f"prompt file vanished: {self.path}: {exc}") from exc

        if self._template is None or current_mtime != self._mtime:
            try:
                source = self.path.read_text(encoding="utf-8")
            except OSError as exc:
                raise SkillLoadError(f"cannot read prompt {self.path}: {exc}") from exc
            self._template = _ENV.from_string(source)
            self._mtime = current_mtime
        return self._template


def load_prompt_source(path: Path) -> PromptSource:
    source = PromptSource(path)
    # Prime the cache so any syntax error surfaces at discovery time, not at first invoke.
    source.get_template()
    return source


def declared_variables(source: str) -> set[str]:
    ast = _ENV.parse(source)
    return meta.find_undeclared_variables(ast)


def render(template: Template, context: dict[str, Any]) -> dict[str, str]:
    """Render a template. Returns dict with 'system' / 'user' block keys if defined,
    otherwise a single 'user' key with the full rendered text."""
    try:
        ctx = template.new_context(context)
        block_names = list(template.blocks.keys())
        if block_names:
            blocks: dict[str, str] = {}
            for name in ("system", "user"):
                if name in template.blocks:
                    blocks[name] = "".join(template.blocks[name](ctx)).strip()
            if blocks:
                return blocks
        rendered = template.render(**context)
    except SkillInvocationError:
        raise
    except Exception as exc:
        raise SkillInvocationError(f"prompt render failed: {exc}") from exc

    return {"user": rendered.strip()}
