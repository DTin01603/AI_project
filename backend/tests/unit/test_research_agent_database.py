from pathlib import Path

from research_agent.database import Database


def test_create_conversation_and_save_messages(tmp_path: Path) -> None:
    db = Database(str(tmp_path / "conversation.db"))
    conversation_id = db.create_conversation()

    user_msg_id = db.save_message(conversation_id, "user", "Xin chào")
    assistant_msg_id = db.save_message(conversation_id, "assistant", "Chào bạn")
    history = db.get_conversation_history(conversation_id)

    assert conversation_id
    assert user_msg_id
    assert assistant_msg_id
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Xin chào"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Chào bạn"
    assert "created_at" in history[0]


def test_save_message_creates_conversation_if_missing(tmp_path: Path) -> None:
    db = Database(str(tmp_path / "conversation.db"))
    conversation_id = "conv-001"

    db.save_message(conversation_id, "user", "Message 1")
    history = db.get_conversation_history(conversation_id)

    assert len(history) == 1
    assert history[0]["content"] == "Message 1"


def test_history_empty_for_unknown_conversation(tmp_path: Path) -> None:
    db = Database(str(tmp_path / "conversation.db"))

    assert db.get_conversation_history("unknown") == []
