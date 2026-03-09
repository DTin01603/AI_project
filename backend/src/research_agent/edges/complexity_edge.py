from research_agent.state import AgentState


def complexity_edge(state: AgentState) -> str:
    """Route from complexity node to simple or complex branch."""
    return "simple" if state.get("query_type") == "simple" else "complex"
