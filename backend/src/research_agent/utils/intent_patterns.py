"""Centralized intent detection patterns for query routing.

This module provides reusable functions for classifying user intents,
reducing duplication across router_node and complexity_node.
"""

from __future__ import annotations


def is_current_date_request(message: str) -> bool:
    """Detect if query is asking for today's date."""
    lowered = message.lower().strip()
    exact_patterns = [
        "hôm nay ngày mấy",
        "hôm nay là ngày mấy",
        "hôm nay là ngày bao nhiêu",
        "ngày hôm nay là ngày mấy",
        "today's date",
        "what date is today",
        "what day is today",
        "today date",
    ]
    if any(pattern in lowered for pattern in exact_patterns):
        return True

    has_today_keyword = any(token in lowered for token in ["hôm nay", "today"])
    has_date_keyword = any(token in lowered for token in ["ngày", "date"])
    has_asking_keyword = any(token in lowered for token in ["mấy", "bao nhiêu", "what"])
    return has_today_keyword and has_date_keyword and has_asking_keyword


def is_time_sensitive_request(message: str) -> bool:
    """Detect if query requires real-time data (prices, weather, etc.)."""
    lowered = message.lower()
    explicit_patterns = [
        "giá vàng hôm nay",
        "giá vàng thế giới hôm nay",
        "gold price today",
    ]
    if any(pattern in lowered for pattern in explicit_patterns):
        return True

    temporal_keywords = [
        "hôm nay",
        "hiện tại",
        "bây giờ",
        "today",
        "current",
        "latest",
        "mới nhất",
    ]
    market_keywords = [
        "giá",
        "price",
        "vàng",
        "gold",
        "usd/ounce",
        "xau",
        "btc",
        "bitcoin",
        "eth",
    ]
    return any(token in lowered for token in temporal_keywords) and any(
        token in lowered for token in market_keywords
    )


def is_research_intent_request(message: str) -> bool:
    """Detect if query requires research/external evidence."""
    lowered = message.lower()
    research_keywords = [
        "so sánh",
        "nghiên cứu",
        "research",
        "phân tích sâu",
        "tìm hiểu",
        "công thức",
        "cách",
        "hướng dẫn",
        "latest",
        "trend",
        "news",
        "mới nhất",
    ]
    return any(keyword in lowered for keyword in research_keywords)


def extract_intent_hints(message: str) -> dict[str, bool]:
    """Extract all intent classifications for a message at once.

    Returns:
        Dict with keys: is_date, is_time_sensitive, is_research
    """
    return {
        "is_date": is_current_date_request(message),
        "is_time_sensitive": is_time_sensitive_request(message),
        "is_research": is_research_intent_request(message),
    }


__all__ = [
    "is_current_date_request",
    "is_time_sensitive_request",
    "is_research_intent_request",
    "extract_intent_hints",
]
