from langchain_core.messages import HumanMessage

from research_agent.nodes.router_node import router_node


def test_router_node_current_date() -> None:
    state = {"messages": [HumanMessage(content="Hôm nay là ngày mấy?")], "execution_metadata": {}}
    result = router_node(state)
    assert result["query_type"] == "current_date"


def test_router_node_research_intent() -> None:
    state = {"messages": [HumanMessage(content="Tìm kiếm quán cà phê top ở Hà Nội")], "execution_metadata": {}}
    result = router_node(state)
    assert result["query_type"] == "research_intent"


def test_router_node_default_direct_llm() -> None:
    state = {"messages": [HumanMessage(content="Giải thích async await")], "execution_metadata": {}}
    result = router_node(state)
    assert result["query_type"] == "direct_llm"
