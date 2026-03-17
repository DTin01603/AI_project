"""Shared utilities for research agent v2."""

from research_agent.utils.intent_patterns import (
    extract_intent_hints,
    is_current_date_request,
    is_research_intent_request,
    is_time_sensitive_request,
)
from research_agent.utils.node_helpers import (
    NodeTimer,
    extract_error_context,
    get_execution_metadata,
    get_last_message_text,
    merge_state_update,
    node_timing_wrapper,
    update_node_timing,
)
from research_agent.utils.parsing import (
    deduplicate_list,
    extract_field_from_json,
    extract_json_from_text,
    extract_sentences,
    flatten_dict,
    parse_json_safe,
)
from research_agent.utils.text import (
    build_numbered_list,
    extract_lines,
    indent_text,
    normalize_whitespace,
    split_markdown_sections,
    truncate,
)

__all__ = [
    # Intent patterns
    "is_current_date_request",
    "is_time_sensitive_request",
    "is_research_intent_request",
    "extract_intent_hints",
    # Node helpers
    "NodeTimer",
    "get_execution_metadata",
    "update_node_timing",
    "node_timing_wrapper",
    "get_last_message_text",
    "merge_state_update",
    "extract_error_context",
    # Parsing
    "extract_json_from_text",
    "parse_json_safe",
    "extract_field_from_json",
    "deduplicate_list",
    "flatten_dict",
    "extract_sentences",
    # Text
    "truncate",
    "normalize_whitespace",
    "extract_lines",
    "indent_text",
    "build_numbered_list",
    "split_markdown_sections",
]
