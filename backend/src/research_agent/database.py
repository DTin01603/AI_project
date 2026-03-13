from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class Database:
    def __init__(self, db_path: str) -> None:
        # Initialize SQLite storage and ensure schema exists.
        self.db_path = db_path
        self._ensure_parent_dir()
        self._initialize_schema()

    def _ensure_parent_dir(self) -> None:
        db_file = Path(self.db_path)
        if db_file.parent and str(db_file.parent) not in {"", "."}:
            db_file.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        try:
            connection.row_factory = sqlite3.Row
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize_schema(self) -> None:
        # Create conversations/messages tables and useful indexes if missing.
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)"
            )
            
            # Create FTS5 virtual table for full-text search
            # Note: We don't use content= and content_rowid= because we want FTS5 to store its own copy
            # This makes triggers simpler and more reliable
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    message_id UNINDEXED,
                    content,
                    tokenize='porter unicode61'
                )
                """
            )
            
            # Create triggers for automatic FTS index synchronization
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS messages_fts_insert 
                AFTER INSERT ON messages BEGIN
                    INSERT INTO messages_fts(message_id, content) 
                    VALUES (new.id, new.content);
                END
                """
            )
            
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS messages_fts_delete 
                AFTER DELETE ON messages BEGIN
                    DELETE FROM messages_fts WHERE message_id = old.id;
                END
                """
            )
            
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS messages_fts_update 
                AFTER UPDATE ON messages BEGIN
                    UPDATE messages_fts SET content = new.content WHERE message_id = new.id;
                END
                """
            )
            
            # Populate FTS index from existing messages if needed
            self._populate_fts_index(conn)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
    
    def _populate_fts_index(self, conn: sqlite3.Connection) -> None:
        """Populate FTS index from existing messages if not already populated."""
        # Check if FTS index is empty
        cursor = conn.execute("SELECT COUNT(*) FROM messages_fts")
        fts_count = cursor.fetchone()[0]
        
        # Check if messages table has data
        cursor = conn.execute("SELECT COUNT(*) FROM messages")
        messages_count = cursor.fetchone()[0]
        
        # If FTS is empty but messages exist, populate the index
        if fts_count == 0 and messages_count > 0:
            conn.execute(
                """
                INSERT INTO messages_fts(message_id, content)
                SELECT id, content FROM messages
                """
            )

    def create_conversation(self, conversation_id: str | None = None) -> str:
        # Create or reuse a conversation identifier.
        resolved_id = conversation_id or str(uuid4())
        now = self._now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO conversations (id, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (resolved_id, now, now),
            )
        return resolved_id

    def save_message(self, conversation_id: str, role: str, content: str) -> str:
        # Persist one chat message and update conversation timestamp.
        self.create_conversation(conversation_id)
        message_id = str(uuid4())
        now = self._now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, conversation_id, role, content, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
        return message_id

    def get_conversation_history(self, conversation_id: str) -> list[dict[str, str]]:
        # Load ordered conversation history for context-aware LLM calls.
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            ).fetchall()

        return [
            {
                "role": str(row["role"]),
                "content": str(row["content"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]
