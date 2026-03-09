from research_agent.state import AgentState

_VALID_ROUTES = {"research_intent", "current_date", "direct_llm"}


def router_edge(state: AgentState) -> str:
    """Route from router node to downstream branch with safe default."""
    route = state.get("query_type")
    if route in _VALID_ROUTES:
        return route
    return "direct_llm"
