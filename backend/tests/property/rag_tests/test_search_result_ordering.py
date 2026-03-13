"""Property-based tests for search result ordering.

Feature: rag-tool-implementation, Property 2: Search Result Ordering
**Validates: Requirements 1.3, 5.3, 7.1**
"""

import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from rag.fts_engine import FTSEngine
from research_agent.database import Database


@st.composite
def search_scenario(draw):
    """Generate a search scenario with multiple messages and a query."""
    num_messages = draw(st.integers(min_value=3, max_value=10))
    search_term = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
            min_size=3,
            max_size=10,
        )
    )

    messages = []
    for _ in range(num_messages):
        repetitions = draw(st.integers(min_value=1, max_value=5))
        content = " ".join([search_term] * repetitions)
        extra_text = draw(
            st.text(
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
                min_size=0,
                max_size=50,
            )
        )
        content = f"{content} {extra_text}".strip()
        messages.append(content)

    return search_term, messages


@settings(max_examples=100, deadline=None)
@given(search_scenario())
def test_search_results_ordered_by_descending_score(scenario):
    """Search results should be ordered by descending score."""
    search_term, messages = scenario
    if not search_term or len(search_term) < 2:
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        db = Database(db_path)
        fts_engine = FTSEngine(db_path)

        conversation_id = "test-conv"
        db.create_conversation(conversation_id)

        for content in messages:
            db.save_message(conversation_id, "user", content)

        results = fts_engine.search(search_term, limit=len(messages))
        if not results:
            return

        for index in range(len(results) - 1):
            assert results[index].score >= results[index + 1].score


@settings(max_examples=100, deadline=None)
@given(search_scenario())
def test_search_scores_in_valid_range(scenario):
    """All scores should remain in the [0.0, 1.0] range."""
    search_term, messages = scenario
    if not search_term or len(search_term) < 2:
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        db = Database(db_path)
        fts_engine = FTSEngine(db_path)

        conversation_id = "test-conv"
        db.create_conversation(conversation_id)

        for content in messages:
            db.save_message(conversation_id, "user", content)

        results = fts_engine.search(search_term, limit=len(messages))
        for result in results:
            assert 0.0 <= result.score <= 1.0


@settings(max_examples=100, deadline=None)
@given(search_scenario(), st.floats(min_value=0.0, max_value=1.0))
def test_min_score_filter(scenario, min_score):
    """All returned scores should respect the min_score filter."""
    search_term, messages = scenario
    if not search_term or len(search_term) < 2:
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        db = Database(db_path)
        fts_engine = FTSEngine(db_path)

        conversation_id = "test-conv"
        db.create_conversation(conversation_id)

        for content in messages:
            db.save_message(conversation_id, "user", content)

        results = fts_engine.search(search_term, limit=len(messages), min_score=min_score)
        for result in results:
            assert result.score >= min_score