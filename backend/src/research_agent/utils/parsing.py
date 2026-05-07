"""Parsing utilities: JSON-from-text + list dedup."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

T = TypeVar("T")


def _extract_json_from_text(text: str) -> Any | None:
    """Extract the first JSON object/array from arbitrary text.

    Handles markdown ```json fences and surrounding prose.
    """
    if not text:
        return None

    cleaned = re.sub(r"```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"```\s*", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def parse_json_safe(text: str, default: T | None = None) -> dict[str, Any] | list[Any] | T | None:
    """Safely parse JSON text (with markdown-fence recovery); return ``default`` on failure."""
    result = _extract_json_from_text(text)
    return result if result is not None else default


def deduplicate_list(
    items: list[T],
    key_func: callable[[T], Any] | None = None,
    preserve_order: bool = True,
) -> list[T]:
    """Deduplicate ``items`` by optional ``key_func``, preserving order by default."""
    if not items:
        return []

    if key_func is None:
        key_func = lambda x: x  # noqa: E731

    if not preserve_order:
        return list({key_func(item): item for item in items}.values())

    seen: set[Any] = set()
    result: list[T] = []
    for item in items:
        key = key_func(item)
        hashable = key
        if isinstance(key, (dict, list)):
            hashable = json.dumps(key, default=str, sort_keys=True)
        if hashable not in seen:
            seen.add(hashable)
            result.append(item)
    return result


__all__ = ["parse_json_safe", "deduplicate_list"]
