from __future__ import annotations

import logging
from typing import Any

from research_agent.nodes.common import extract_last_message_content
from research_agent.state import AgentState
from research_agent.utils import get_execution_metadata, node_timing_wrapper
from skills import SkillNotFoundError, get_registry

logger = logging.getLogger(__name__)

_VALID_INTENTS = {"direct_answer", "local_rag", "web_search", "current_date"}


@node_timing_wrapper("intent")
def intent_node(state: AgentState) -> dict[str, Any]:
    """Single-call LLM intent classifier.

    Replaces the legacy complexity_classifier + query_router two-step pipeline.
    Routes the user query into one of:
        - direct_answer  → simple_llm (no retrieval)
        - local_rag      → rag_subgraph (deep retrieval, MAX_RETRIES allowed)
        - web_search     → planning → research → synthesis
        - current_date   → current_date_node
    """
    message = extract_last_message_content(state)
    metadata = get_execution_metadata(state)
    fallback_used = state.get("fallback_used", False)

    if not message.strip():
        intent = "direct_answer"
        confidence = 1.0
        reason = "empty_message_default"
    else:
        model_override = metadata.get("model") or None
        try:
            skill = get_registry().get("intent_classifier")
            result = skill.invoke({"message": message}, model_override=model_override)
            intent = result.get("intent", "direct_answer")
            confidence = float(result.get("confidence", 0.5))
            reason = str(result.get("reason", "model_classification"))
            if intent not in _VALID_INTENTS:
                intent = "direct_answer"
                reason = f"invalid_intent_default:{reason}"
        except SkillNotFoundError:
            logger.exception("intent_classifier skill missing")
            raise
        except Exception:
            logger.exception("intent_classifier failed; defaulting to direct_answer")
            intent = "direct_answer"
            confidence = 0.0
            reason = "skill_error_default"
            fallback_used = True

    logger.info("[INTENT] message=%r | intent=%s | confidence=%.2f | reason=%s",
                message[:120], intent, confidence, reason)

    metadata.setdefault("routing", {})
    metadata["routing"]["intent"] = {
        "intent": intent,
        "confidence": confidence,
        "reason": reason,
    }

    return {
        "query_type": intent,
        "execution_metadata": metadata,
        "fallback_used": fallback_used,
    }
