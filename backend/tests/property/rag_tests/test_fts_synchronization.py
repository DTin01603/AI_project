"""Property-based tests for FTS synchronization.

Feature: rag-tool-implementation, Property 1: FTS Index Synchronization
**Validates: Requirements 1.2, 1.5**
"""

import re
import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from research_agent.database import Database


def escape_fts5_term(term: str) -> str:
    """Escape special FTS5 characters in search term."""
    escaped = re.sub(r"[^a-zA-Z0-9\s]", " ", term)
    escaped = " ".join(escaped.split())
    return escaped


@st.composite
def message_data(draw):
    """Generate random message data for testing."""
    conversation_id = draw(st.uuids()).hex
    role = draw(st.sampled_from(["user", "assistant", "system"]))
    content = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "P", "Zs"),
                min_codepoint=32,
                max_codepoint=126,
            ),
            min_size=1,
            max_size=500,
        )
    )
    return conversation_id, role, content


@settings(max_examples=100, deadline=None)
@given(message_data())
def test_fts_insert_synchronization(message_data_tuple):
    """Inserted messages should be findable via FTS search."""
    conversation_id, role, content = message_data_tuple
    if not content or not content.strip():
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        temp_db = Database(db_path)

        message_id = temp_db.save_message(conversation_id, role, content)

        words = content.split()
        if not words:
            return

        search_term = None
        for word in words:
            cleaned = word.strip()
            if cleaned and len(cleaned) > 1:
                search_term = escape_fts5_term(cleaned)
                if search_term and search_term.strip() and len(search_term.strip()) > 1:
                    break
                search_term = None

        if not search_term:
            return

        with temp_db._connect() as conn:
            cursor = conn.execute(
                """
                SELECT m.id, m.content
                FROM messages m
                JOIN messages_fts fts ON m.id = fts.message_id
                WHERE messages_fts MATCH ?
                """,
                (search_term,),
            )
            results = cursor.fetchall()

        found_ids = [row[0] for row in results]
        assert message_id in found_ids


@settings(max_examples=100, deadline=None)
@given(message_data())
def test_fts_delete_synchronization(message_data_tuple):
    """Deleted messages should be removed from the FTS index."""
    conversation_id, role, content = message_data_tuple
    if not content or not content.strip():
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        temp_db = Database(db_path)

        message_id = temp_db.save_message(conversation_id, role, content)

        with temp_db._connect() as conn:
            conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))

        with temp_db._connect() as conn:
            cursor = conn.execute("SELECT message_id FROM messages_fts WHERE message_id = ?", (message_id,))
            result = cursor.fetchone()

        assert result is None


@settings(max_examples=100, deadline=None)
@given(message_data(), st.text(min_size=1, max_size=500))
def test_fts_update_synchronization(message_data_tuple, new_content):
    """Updated messages should keep FTS content in sync."""
    conversation_id, role, content = message_data_tuple
    if not content or not content.strip() or not new_content or not new_content.strip():
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        temp_db = Database(db_path)

        message_id = temp_db.save_message(conversation_id, role, content)

        with temp_db._connect() as conn:
            conn.execute(
                "UPDATE messages SET content = ? WHERE id = ?",
                (new_content, message_id),
            )

        with temp_db._connect() as conn:
            cursor = conn.execute("SELECT content FROM messages_fts WHERE message_id = ?", (message_id,))
            result = cursor.fetchone()

        assert result is not None
        assert result[0] == new_content