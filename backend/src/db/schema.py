from __future__ import annotations

from db.connection import SQLiteConnectionFactory


_CONVERSATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
)
"""

_MESSAGES_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    message_id UNINDEXED,
    content,
    tokenize='porter unicode61'
)
"""

_FTS_INSERT_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS messages_fts_insert
AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(message_id, content)
    VALUES (new.id, new.content);
END
"""

_FTS_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS messages_fts_delete
AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE message_id = old.id;
END
"""

_FTS_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS messages_fts_update
AFTER UPDATE ON messages BEGIN
    UPDATE messages_fts SET content = new.content WHERE message_id = new.id;
END
"""

_CITATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS citations (
    citation_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_id TEXT,
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    created_at TEXT,
    metadata_json TEXT,
    available INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
)
"""

_CITATION_USAGE_TABLE = """
CREATE TABLE IF NOT EXISTS citation_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    citation_id TEXT NOT NULL,
    query TEXT NOT NULL,
    used_in_response INTEGER NOT NULL,
    used_at TEXT NOT NULL,
    FOREIGN KEY(citation_id) REFERENCES citations(citation_id)
)
"""

_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    chunk_count INTEGER NOT NULL,
    metadata_json TEXT
)
"""


def run_migrations(connection_factory: SQLiteConnectionFactory) -> None:
    """Apply full schema (tables, triggers, indexes) idempotently.

    Replaces the per-class _ensure_schema() / _initialize_schema() that
    previously lived in research_agent/database.py, rag/citation_tracker.py
    and rag/document_indexer.py. Safe to call multiple times.
    """
    with connection_factory.transaction() as conn:
        conn.execute(_CONVERSATIONS_TABLE)
        conn.execute(_MESSAGES_TABLE)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id "
            "ON messages(conversation_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_created_at "
            "ON messages(created_at)"
        )
        conn.execute(_MESSAGES_FTS_TABLE)
        conn.execute(_FTS_INSERT_TRIGGER)
        conn.execute(_FTS_DELETE_TRIGGER)
        conn.execute(_FTS_UPDATE_TRIGGER)
        conn.execute(_CITATIONS_TABLE)
        conn.execute(_CITATION_USAGE_TABLE)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_citation_usage_citation "
            "ON citation_usage(citation_id)"
        )
        conn.execute(_DOCUMENTS_TABLE)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_source_type "
            "ON documents(source_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_modified_at "
            "ON documents(modified_at)"
        )
        _backfill_messages_fts(conn)


def _backfill_messages_fts(conn) -> None:
    """Populate messages_fts from messages if empty (legacy data carry-over)."""
    fts_count = conn.execute("SELECT COUNT(*) FROM messages_fts").fetchone()[0]
    messages_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    if fts_count == 0 and messages_count > 0:
        conn.execute(
            "INSERT INTO messages_fts(message_id, content) "
            "SELECT id, content FROM messages"
        )
