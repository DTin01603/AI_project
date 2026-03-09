from research_agent.edges.complexity_edge import complexity_edge
from research_agent.edges.router_edge import router_edge


def test_complexity_edge_simple_path() -> None:
    assert complexity_edge({"query_type": "simple"}) == "simple"


def test_complexity_edge_complex_path() -> None:
    assert complexity_edge({"query_type": "complex"}) == "complex"


def test_router_edge_routes_known_values() -> None:
    assert router_edge({"query_type": "research_intent"}) == "research_intent"
    assert router_edge({"query_type": "current_date"}) == "current_date"
    assert router_edge({"query_type": "direct_llm"}) == "direct_llm"


def test_router_edge_defaults_for_invalid_value() -> None:
    assert router_edge({"query_type": "unexpected"}) == "direct_llm"
