from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

from skills._base import BaseSkill
from skills._errors import SkillLoadError, SkillNotFoundError
from skills._prompt_loader import load_prompt_source

logger = logging.getLogger("skills")


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._discovered_root: Path | None = None

    def discover(self, root: Path) -> None:
        root = Path(root)
        if not root.is_dir():
            raise SkillLoadError(f"skills root not found: {root}")

        self._discovered_root = root
        for folder in sorted(root.iterdir()):
            if not folder.is_dir():
                continue
            if folder.name.startswith("_"):
                continue
            self._load_folder_recursive(folder, prefix="")

        logger.info("[SKILLS] discovered %d skill(s): %s", len(self._skills), sorted(self._skills.keys()))

    def _load_folder_recursive(self, folder: Path, *, prefix: str) -> None:
        yaml_path = folder / "skill.yaml"
        handler_path = folder / "handler.py"

        if yaml_path.is_file() and handler_path.is_file():
            full_name = f"{prefix}{folder.name}" if prefix else folder.name
            try:
                skill = self._load_skill(folder, default_name=full_name)
            except Exception as exc:
                logger.error("[SKILLS] failed to load %s: %s", full_name, exc)
                return
            self._skills[skill.name] = skill
            logger.info("[SKILLS] loaded %s v%s", skill.name, skill.version)
            return

        for child in sorted(folder.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith("_"):
                continue
            self._load_folder_recursive(
                child,
                prefix=f"{prefix}{folder.name}." if not prefix else f"{prefix}{folder.name}.",
            )

    def _load_skill(self, folder: Path, *, default_name: str) -> BaseSkill:
        yaml_path = folder / "skill.yaml"
        handler_path = folder / "handler.py"
        prompt_path = folder / "prompt.md"

        config: dict[str, Any] = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        name = config.get("name") or default_name
        version = config.get("version", 1)

        prompt_source = None
        if prompt_path.is_file():
            prompt_source = load_prompt_source(prompt_path)

        module_name = f"_skill_{name.replace('.', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, handler_path)
        if spec is None or spec.loader is None:
            raise SkillLoadError(f"cannot build module spec for {handler_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        handler_cls = getattr(module, "Handler", None)
        if handler_cls is None:
            raise SkillLoadError(f"{handler_path} does not define `Handler` class")
        if not issubclass(handler_cls, BaseSkill):
            raise SkillLoadError(f"{handler_path}:Handler must subclass BaseSkill")

        return handler_cls(
            name=name,
            version=version,
            config=config,
            prompt_source=prompt_source,
        )

    def get(self, name: str) -> BaseSkill:
        try:
            return self._skills[name]
        except KeyError:
            raise SkillNotFoundError(f"skill not found: {name!r}. available: {sorted(self._skills)}") from None

    def has(self, name: str) -> bool:
        return name in self._skills

    def names(self) -> list[str]:
        return sorted(self._skills.keys())


_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry


def reset_registry() -> None:
    """For tests only."""
    global _registry
    _registry = None
