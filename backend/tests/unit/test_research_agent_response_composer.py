from research_agent.response_composer import ResponseComposer


def test_response_composer_returns_default_when_knowledge_empty() -> None:
    composer = ResponseComposer()

    answer = composer.compose("Câu hỏi", "")

    assert "chưa thu thập" in answer.lower()
