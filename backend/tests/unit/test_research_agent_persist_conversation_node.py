from langchain_core.messages import HumanMessage

from research_agent.nodes.persist_conversation_node import persist_conversation_node


class _FakeConversationService:
    def __init__(self) -> None:
        self.created: list[str | None] = []
        self.persisted_turns: list[tuple[str, str, str]] = []

    def get_or_create_conversation(self, conversation_id: str | None) -> str:
        resolved = conversation_id or "conv-generated"
        self.created.append(resolved)
        return resolved

    def persist_turn(
        self, conversation_id: str, user_message: str, assistant_message: str
    ) -> tuple[str | None, str | None]:
        self.persisted_turns.append((conversation_id, user_message, assistant_message))
        return ("user-id", "assistant-id")


def test_persist_conversation_node_saves_user_and_assistant_messages() -> None:
    service = _FakeConversationService()
    state = {
        "messages": [HumanMessage(content="Xin chào")],
        "final_answer": "Chào bạn!",
        "execution_metadata": {
            "conversation_id": "conv-1",
            "node_timings": {},
        },
    }

    result = persist_conversation_node(state, service)

    assert result["execution_metadata"]["conversation_id"] == "conv-1"
    assert service.persisted_turns == [("conv-1", "Xin chào", "Chào bạn!")]
    assert result["execution_metadata"]["persistence"]["saved"] is True
    assert result["execution_metadata"]["persistence"]["error"] is None
