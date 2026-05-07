from research_agent.state import AgentState

_VALID_INTENTS = {"direct_answer", "local_rag", "web_search", "current_date"}


def intent_edge(state: AgentState) -> str:
    """Route from intent_node to one of the four downstream branches.

    Falls back to direct_answer if the state value is invalid (defensive).
    """
    intent = state.get("query_type")
    if intent in _VALID_INTENTS:
        return intent
    return "direct_answer"
