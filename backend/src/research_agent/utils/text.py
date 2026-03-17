"""Centralized text processing utilities.

Consolidates text operations used across multiple nodes and components.
"""

from __future__ import annotations


def truncate(
    text: str,
    max_chars: int = 600,
    suffix: str = "...",
) -> str:
    """Truncate text to max length with optional suffix.
    
    Args:
        text: Text to truncate
        max_chars: Maximum character count
        suffix: String appended if truncated (included in max_chars)
    
    Returns:
        Original text if under limit, else truncated + suffix
    """
    if len(text) <= max_chars:
        return text
    available = max(0, max_chars - len(suffix))
    return text[:available] + suffix


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace: strip + collapse internal spaces."""
    return " ".join(text.strip().split())


def extract_lines(text: str, max_lines: int | None = None) -> list[str]:
    """Split text into lines, optionally limit count."""
    lines = text.strip().split("\n")
    if max_lines is not None:
        lines = lines[:max_lines]
    return lines


def indent_text(text: str, indent: str = "  ", lines_to_indent: int | None = None) -> str:
    """Indent each line of text.
    
    Args:
        text: Text to indent
        indent: Indent string (default: 2 spaces)
        lines_to_indent: If set, only indent first N lines
    
    Returns:
        Indented text
    """
    lines = text.split("\n")
    if lines_to_indent is not None:
        lines = [indent + line if i < lines_to_indent else line 
                 for i, line in enumerate(lines)]
    else:
        lines = [indent + line for line in lines]
    return "\n".join(lines)


def build_numbered_list(items: list[str], bullet: str = "[{i}]") -> str:
    """Build numbered bullet-point list.
    
    Args:
        items: List of items
        bullet: Format string with {i} placeholder (default: "[{i}]")
    
    Returns:
        Formatted string like "[1] item1\n[2] item2"
    """
    if not items:
        return ""
    return "\n".join(
        f"{bullet.format(i=idx)} {item}"
        for idx, item in enumerate(items, start=1)
    )


def split_markdown_sections(text: str, heading_level: int = 2) -> dict[str, str]:
    """Split markdown by heading level into sections.
    
    Args:
        text: Markdown text
        heading_level: Heading level to split by (1-6)
    
    Returns:
        Dict with section names as keys, content as values
    """
    heading_prefix = "#" * heading_level
    sections: dict[str, str] = {}
    current_section = "__intro__"
    current_content: list[str] = []

    for line in text.split("\n"):
        if line.startswith(heading_prefix + " "):
            if current_content or current_section != "__intro__":
                sections[current_section] = "\n".join(current_content).strip()
            current_section = line.replace(heading_prefix, "").strip()
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections[current_section] = "\n".join(current_content).strip()

    return {k: v for k, v in sections.items() if v}


__all__ = [
    "truncate",
    "normalize_whitespace",
    "extract_lines",
    "indent_text",
    "build_numbered_list",
    "split_markdown_sections",
]
