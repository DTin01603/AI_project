from langchain_core.messages import HumanMessage

from research_agent.nodes.persist_conversation_node import persist_conversation_node


class _FakeDatabase:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.saved: list[tuple[str, str, str]] = []

    def create_conversation(self, conversation_id: str | None = None) -> str:
        resolved = conversation_id or "conv-generated"
        self.created.append(resolved)
        return resolved

    def save_message(self, conversation_id: str, role: str, content: str) -> str:
        self.saved.append((conversation_id, role, content))
        return "msg-id"


def test_persist_conversation_node_saves_user_and_assistant_messages() -> None:
    database = _FakeDatabase()
    state = {
        "messages": [HumanMessage(content="Xin chào")],
        "final_answer": "Chào bạn!",
        "execution_metadata": {
            "conversation_id": "conv-1",
            "node_timings": {},
        },
    }

    result = persist_conversation_node(state, database)

    assert result["execution_metadata"]["conversation_id"] == "conv-1"
    assert database.saved == [
        ("conv-1", "user", "Xin chào"),
        ("conv-1", "assistant", "Chào bạn!"),
    ]
