"""Centralized parsing utilities for JSON, objects, and data extraction.

Consolidates parsing logic used across multiple components.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def extract_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract first JSON object/array from text.
    
    Handles:
    - JSON wrapped in markdown code blocks
    - JSON with surrounding text
    - Malformed JSON (attempts recovery)
    
    Args:
        text: Text containing JSON
    
    Returns:
        Parsed dict/list or None if extraction fails
    """
    if not text:
        return None

    # Remove markdown code blocks
    cleaned = re.sub(r"```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"```\s*", "", cleaned)

    # Try direct JSON parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object/array within text
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def parse_json_safe(
    text: str,
    default: T | None = None,
) -> dict[str, Any] | list[Any] | T | None:
    """Safely parse JSON text with fallback.
    
    Args:
        text: JSON text
        default: Value to return on parse failure
    
    Returns:
        Parsed object or default
    """
    result = extract_json_from_text(text)
    if result is not None:
        return result
    return default


def extract_field_from_json(
    text: str,
    field_path: str,
    default: Any = None,
) -> Any:
    """Extract nested field from JSON text.
    
    Args:
        text: JSON text
        field_path: Dot-separated path (e.g., "message.content.text")
        default: Return if field not found
    
    Returns:
        Field value or default
    """
    obj = extract_json_from_text(text)
    if obj is None:
        return default

    for key in field_path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, (list, tuple)):
            try:
                obj = obj[int(key)]
            except (ValueError, IndexError):
                return default
        else:
            return default

    return obj if obj is not None else default


def deduplicate_list(
    items: list[T],
    key_func: callable[[T], Any] | None = None,
    preserve_order: bool = True,
) -> list[T]:
    """Remove duplicates from list.
    
    Args:
        items: List to deduplicate
        key_func: Function to extract comparison key (default: identity)
        preserve_order: Keep original order if True (slower but ordered)
    
    Returns:
        Deduplicated list
    """
    if not items:
        return []

    if key_func is None:
        key_func = lambda x: x

    if preserve_order:
        seen: set[Any] = set()
        result: list[T] = []
        for item in items:
            key = key_func(item)
            try:
                hashable = key
                if isinstance(key, (dict, list)):
                    hashable = json.dumps(key, default=str, sort_keys=True)
            except Exception:
                hashable = str(key)

            if hashable not in seen:
                seen.add(hashable)
                result.append(item)
        return result
    else:
        return list({key_func(item): item for item in items}.values())


def flatten_dict(
    d: dict[str, Any],
    parent_key: str = "",
    sep: str = ".",
) -> dict[str, Any]:
    """Flatten nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Prefix for keys
        sep: Separator between keys
    
    Returns:
        Flattened dictionary
    """
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, (list, tuple)):
            for i, item in enumerate(v):
                items.append((f"{new_key}[{i}]", item))
        else:
            items.append((new_key, v))
    return dict(items)


def extract_sentences(text: str, min_length: int = 5) -> list[str]:
    """Split text into sentences.
    
    Args:
        text: Text to split
        min_length: Minimum characters per sentence
    
    Returns:
        List of sentences
    """
    # Split on sentence-ending punctuation
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) >= min_length]


__all__ = [
    "extract_json_from_text",
    "parse_json_safe",
    "extract_field_from_json",
    "deduplicate_list",
    "flatten_dict",
    "extract_sentences",
]
