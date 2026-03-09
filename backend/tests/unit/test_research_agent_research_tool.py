from research_agent.research_tool import ResearchTool


def test_research_tool_search_limits_top_results() -> None:
    def _search_executor(query: str, max_results: int):
        return [
            {"title": "A", "url": "https://a", "snippet": "a"},
            {"title": "B", "url": "https://b", "snippet": "b"},
            {"title": "C", "url": "https://c", "snippet": "c"},
            {"title": "D", "url": "https://d", "snippet": "d"},
        ]

    tool = ResearchTool(
        tavily_api_key=None,
        llm_api_key=None,
        max_results=3,
        search_executor=_search_executor,
    )

    results = tool._search("test")

    assert len(results) == 3
    assert results[0].title == "A"
    assert results[2].title == "C"


def test_research_tool_execute_task_contains_sources() -> None:
    def _search_executor(query: str, max_results: int):
        return [
            {"title": "A", "url": "https://a", "snippet": "alpha"},
            {"title": "B", "url": "https://b", "snippet": "beta"},
        ]

    tool = ResearchTool(
        tavily_api_key=None,
        llm_api_key=None,
        max_results=3,
        search_executor=_search_executor,
    )

    result = tool.execute_task(task_order=1, query="q", goal="g")

    assert result.success is True
    assert result.task_order == 1
    assert "https://a" in result.sources
    assert "https://b" in result.sources
