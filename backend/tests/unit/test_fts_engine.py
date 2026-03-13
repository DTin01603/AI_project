"""Unit tests for FTS Engine.

Tests phrase queries, prefix matching, boolean operators, error handling,
and performance with 10K messages.

**Validates: Requirements 1.3, 1.4**
"""

import time
from pathlib import Path

import importlib
import sys
import time
from pathlib import Path

import pytest

# Explicitly load modules from src to avoid test directory conflicts
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

# Force reload to get the right module
if "rag" in sys.modules:
    del sys.modules["rag"]
if "rag.fts_engine" in sys.modules:
    del sys.modules["rag.fts_engine"]

from rag.fts_engine import FTSEngine
from research_agent.database import Database


@pytest.fixture
def fts_setup(tmp_path: Path):
    """Create a database and FTS engine for testing."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    fts_engine = FTSEngine(db_path)
    
    # Create a test conversation
    conversation_id = "test-conv"
    db.create_conversation(conversation_id)
    
    return db, fts_engine, conversation_id


def test_phrase_query(fts_setup):
    """Test phrase queries with exact matching.
    
    **Validates: Requirements 1.3, 1.4**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add messages
    db.save_message(conversation_id, "user", "The quick brown fox jumps over the lazy dog")
    db.save_message(conversation_id, "user", "A quick fox and a brown dog")
    db.save_message(conversation_id, "user", "The lazy dog sleeps")
    
    # Search for exact phrase
    results = fts_engine.search('"quick brown fox"')
    
    # Should only match the first message
    assert len(results) == 1
    assert "quick brown fox" in results[0].content.lower()


def test_prefix_matching(fts_setup):
    """Test prefix matching with wildcard operator.
    
    **Validates: Requirements 1.3, 1.4**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add messages with various forms of "test"
    db.save_message(conversation_id, "user", "This is a test message")
    db.save_message(conversation_id, "user", "Testing the system")
    db.save_message(conversation_id, "user", "The tester found a bug")
    db.save_message(conversation_id, "user", "No match here")
    
    # Search with prefix
    results = fts_engine.search("test*")
    
    # Should match first three messages
    assert len(results) == 3
    for result in results:
        assert any(
            word.lower().startswith("test")
            for word in result.content.split()
        )


def test_boolean_and_operator(fts_setup):
    """Test AND boolean operator.
    
    **Validates: Requirements 1.3, 1.4**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add messages
    db.save_message(conversation_id, "user", "Python is a programming language")
    db.save_message(conversation_id, "user", "Python is great")
    db.save_message(conversation_id, "user", "Programming is fun")
    
    # Search with AND
    results = fts_engine.search("Python AND programming")
    
    # Should only match the first message
    assert len(results) == 1
    assert "Python" in results[0].content
    assert "programming" in results[0].content


def test_boolean_or_operator(fts_setup):
    """Test OR boolean operator.
    
    **Validates: Requirements 1.3, 1.4**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add messages
    db.save_message(conversation_id, "user", "I like Python")
    db.save_message(conversation_id, "user", "I like JavaScript")
    db.save_message(conversation_id, "user", "I like coffee")
    
    # Search with OR
    results = fts_engine.search("Python OR JavaScript")
    
    # Should match first two messages
    assert len(results) == 2


def test_boolean_not_operator(fts_setup):
    """Test NOT boolean operator.
    
    **Validates: Requirements 1.3, 1.4**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add messages
    db.save_message(conversation_id, "user", "Python programming language")
    db.save_message(conversation_id, "user", "Python snake")
    db.save_message(conversation_id, "user", "Java programming language")
    
    # Search with NOT
    results = fts_engine.search("Python NOT snake")
    
    # Should only match the first message
    assert len(results) == 1
    assert "programming" in results[0].content


def test_conversation_filter(fts_setup):
    """Test filtering by conversation_id.
    
    **Validates: Requirements 1.3, 1.4**
    """
    db, fts_engine, _ = fts_setup
    
    # Create two conversations
    conv1 = "conv-1"
    conv2 = "conv-2"
    db.create_conversation(conv1)
    db.create_conversation(conv2)
    
    # Add messages to both
    db.save_message(conv1, "user", "Python is great")
    db.save_message(conv2, "user", "Python is awesome")
    
    # Search with conversation filter
    results = fts_engine.search("Python", filters={"conversation_id": conv1})
    
    # Should only match conv1
    assert len(results) == 1
    assert results[0].metadata["conversation_id"] == conv1


def test_date_range_filter(fts_setup):
    """Test filtering by date range.
    
    **Validates: Requirements 1.3, 1.4**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add messages (they'll have timestamps)
    db.save_message(conversation_id, "user", "First message")
    
    # Get the timestamp of the first message
    with db._connect() as conn:
        cursor = conn.execute(
            "SELECT created_at FROM messages ORDER BY created_at LIMIT 1"
        )
        first_timestamp = cursor.fetchone()[0]
    
    # Add more messages
    db.save_message(conversation_id, "user", "Second message")
    db.save_message(conversation_id, "user", "Third message")
    
    # Get the timestamp of the last message
    with db._connect() as conn:
        cursor = conn.execute(
            "SELECT created_at FROM messages ORDER BY created_at DESC LIMIT 1"
        )
        last_timestamp = cursor.fetchone()[0]
    
    # Search with date range that includes all messages
    results = fts_engine.search(
        "message",
        filters={"date_range": (first_timestamp, last_timestamp)},
    )
    
    # Should match all three messages
    assert len(results) == 3


def test_empty_query(fts_setup):
    """Test handling of empty query.
    
    **Validates: Requirements 1.4**
    """
    _, fts_engine, _ = fts_setup
    
    # Empty query should return empty results
    results = fts_engine.search("")
    assert len(results) == 0
    
    # Whitespace-only query should return empty results
    results = fts_engine.search("   ")
    assert len(results) == 0


def test_invalid_query_syntax(fts_setup):
    """Test handling of invalid FTS5 query syntax.
    
    **Validates: Requirements 1.4**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add a message
    db.save_message(conversation_id, "user", "Test message")
    
    # Invalid queries should raise OperationalError or return empty results
    # FTS5 is quite forgiving, so some "invalid" queries might still work
    # Test with unmatched quotes
    try:
        results = fts_engine.search('"unmatched quote')
        # If it doesn't raise an error, it should return empty or valid results
        assert isinstance(results, list)
    except Exception as e:
        # Should be a database error
        assert "sqlite" in str(type(e)).lower() or "operational" in str(type(e)).lower()


def test_limit_parameter(fts_setup):
    """Test limit parameter restricts result count.
    
    **Validates: Requirements 1.3**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add 10 messages
    for i in range(10):
        db.save_message(conversation_id, "user", f"Test message number {i}")
    
    # Search with limit
    results = fts_engine.search("Test", limit=5)
    
    # Should return exactly 5 results
    assert len(results) == 5


def test_min_score_threshold(fts_setup):
    """Test min_score parameter filters low-scoring results.
    
    **Validates: Requirements 1.3**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add messages with varying relevance
    db.save_message(conversation_id, "user", "Python Python Python")
    db.save_message(conversation_id, "user", "Python programming")
    db.save_message(conversation_id, "user", "I like Python")
    
    # Search with high min_score
    results = fts_engine.search("Python", min_score=0.8)
    
    # Should filter out lower-scoring results
    assert len(results) <= 3
    for result in results:
        assert result.score >= 0.8


def test_performance_10k_messages(tmp_path: Path):
    """Test search performance with 10,000 messages.
    
    **Validates: Requirements 1.3**
    """
    db_path = str(tmp_path / "large_test.db")
    db = Database(db_path)
    fts_engine = FTSEngine(db_path)
    
    conversation_id = "large-conv"
    db.create_conversation(conversation_id)
    
    # Add 10,000 messages
    for i in range(10000):
        content = f"Message number {i} with some test content"
        if i % 100 == 0:
            content += " special keyword"
        db.save_message(conversation_id, "user", content)
    
    # Measure search time
    start_time = time.time()
    results = fts_engine.search("special keyword", limit=200)  # Increase limit to get all results
    elapsed_time = time.time() - start_time
    
    # Should complete within 100ms (requirement: < 100ms for 10K messages)
    assert elapsed_time < 0.1, f"Search took {elapsed_time:.3f}s, expected < 0.1s"
    
    # Should find approximately 100 messages (every 100th message)
    assert 90 <= len(results) <= 110


def test_rebuild_index(fts_setup):
    """Test index rebuild functionality.
    
    **Validates: Requirements 1.3**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add messages
    db.save_message(conversation_id, "user", "Test message one")
    db.save_message(conversation_id, "user", "Test message two")
    
    # Verify search works
    results = fts_engine.search("Test")
    assert len(results) == 2
    
    # Rebuild index
    fts_engine.rebuild_index()
    
    # Verify search still works after rebuild
    results = fts_engine.search("Test")
    assert len(results) == 2


def test_metadata_preservation(fts_setup):
    """Test that search results include proper metadata.
    
    **Validates: Requirements 1.3**
    """
    db, fts_engine, conversation_id = fts_setup
    
    # Add a message
    db.save_message(conversation_id, "user", "Test message")
    
    # Search and verify metadata
    results = fts_engine.search("Test")
    
    assert len(results) == 1
    result = results[0]
    
    # Check metadata fields
    assert "conversation_id" in result.metadata
    assert "role" in result.metadata
    assert "created_at" in result.metadata
    assert result.metadata["conversation_id"] == conversation_id
    assert result.metadata["role"] == "user"
    assert result.source_type == "conversation"
