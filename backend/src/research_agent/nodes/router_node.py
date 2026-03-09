from __future__ import annotations

from time import perf_counter
from typing import Any

from research_agent.state import AgentState


def _extract_last_message_content(state: AgentState) -> str:
    messages = state.get("messages") or []
    if not messages:
        return ""
    content = getattr(messages[-1], "content", "")
    return content if isinstance(content, str) else str(content)


def _is_current_date_request(message: str) -> bool:
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


def _is_time_sensitive_request(message: str) -> bool:
    lowered = message.lower()
    explicit_patterns = ["giá vàng hôm nay", "giá vàng thế giới hôm nay", "gold price today"]
    if any(pattern in lowered for pattern in explicit_patterns):
        return True

    temporal_keywords = ["hôm nay", "hiện tại", "bây giờ", "today", "current", "latest", "mới nhất"]
    market_keywords = ["giá", "price", "vàng", "gold", "usd/ounce", "xau", "btc", "bitcoin", "eth"]
    return any(token in lowered for token in temporal_keywords) and any(token in lowered for token in market_keywords)


def _is_research_intent_request(message: str) -> bool:
    lowered = message.lower()
    intent_keywords = ["tìm kiếm", "tra cứu", "search", "tìm thông tin", "thông tin"]
    evidence_keywords = ["quán", "nhà hàng", "địa chỉ", "địa điểm", "danh sách", "top", "review", "ở ", "tại "]
    return any(token in lowered for token in intent_keywords) and any(token in lowered for token in evidence_keywords)


def router_node(state: AgentState) -> dict[str, Any]:
    """Route complex queries into research/date/direct_llm branches."""
    started = perf_counter()
    message = _extract_last_message_content(state)

    if _is_current_date_request(message):
        route = "current_date"
        reason = "current_date_detected"
    elif _is_time_sensitive_request(message) or _is_research_intent_request(message):
        route = "research_intent"
        reason = "research_or_time_sensitive"
    else:
        route = "direct_llm"
        reason = "default_direct_llm"

    metadata = dict(state.get("execution_metadata") or {})
    metadata.setdefault("node_timings", {})
    metadata.setdefault("routing", {})
    metadata["node_timings"]["router"] = (perf_counter() - started) * 1000
    metadata["routing"]["router"] = {"route": route, "reason": reason}

    return {
        "query_type": route,
        "execution_metadata": metadata,
    }
