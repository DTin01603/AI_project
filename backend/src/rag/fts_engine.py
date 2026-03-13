"""Full-Text Search Engine using SQLite FTS5.

This module provides the FTSEngine class for keyword-based search
over conversation messages using SQLite's FTS5 extension.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SearchResult:
    """Result from a full-text search operation."""

    id: str
    content: str
    score: float  # Normalized BM25 score in range [0, 1]
    metadata: dict[str, Any]
    source_type: str = "conversation"


class FTSEngine:
    """Full-text search engine using SQLite FTS5.
    
    Provides fast keyword-based search over conversation messages with:
    - BM25 ranking with score normalization
    - Phrase queries, prefix matching, boolean operators
    - Metadata filtering (conversation_id, date range)
    """

    def __init__(self, db_path: str):
        """Initialize FTS engine with database path.
        
        Args:
            db_path: Path to SQLite database with FTS5 tables
        """
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        """Create a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _execute_query(self, sql: str, params: tuple | list) -> list[sqlite3.Row]:
        """Execute a query and return results, properly closing the connection."""
        conn = self._connect()
        try:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()
        finally:
            conn.close()
    
    def _execute_command(self, sql: str, params: tuple | list) -> None:
        """Execute a command (INSERT/UPDATE/DELETE), properly closing the connection."""
        conn = self._connect()
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def index_message(self, message_id: str, content: str) -> None:
        """Index a single message for full-text search.
        
        Note: This is typically handled automatically by database triggers,
        but this method is provided for manual indexing if needed.
        
        Args:
            message_id: Unique message identifier
            content: Message content to index
        """
        self._execute_command(
            "INSERT OR REPLACE INTO messages_fts(message_id, content) VALUES (?, ?)",
            (message_id, content),
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Execute FTS5 search with ranking.
        
        Args:
            query: Search query with FTS5 syntax support:
                - Phrase queries: "exact phrase"
                - Prefix matching: term*
                - Boolean operators: term1 AND term2, term1 OR term2, NOT term
            limit: Maximum results to return
            min_score: Minimum BM25 score threshold (0-1 range after normalization)
            filters: Optional metadata filters:
                - conversation_id: Filter by conversation
                - date_range: Tuple of (start_date, end_date) as ISO strings
                
        Returns:
            List of SearchResult ordered by descending relevance score
        """
        if not query or not query.strip():
            return []

        filters = filters or {}
        
        # Build the query with filters
        sql_parts = [
            """
            SELECT 
                m.id,
                m.content,
                m.conversation_id,
                m.role,
                m.created_at,
                bm25(messages_fts) as raw_score
            FROM messages m
            JOIN messages_fts ON m.id = messages_fts.message_id
            WHERE messages_fts MATCH ?
            """
        ]
        params: list[Any] = [query]

        # Add conversation filter
        if "conversation_id" in filters:
            sql_parts.append("AND m.conversation_id = ?")
            params.append(filters["conversation_id"])

        # Add date range filter
        if "date_range" in filters:
            start_date, end_date = filters["date_range"]
            sql_parts.append("AND m.created_at BETWEEN ? AND ?")
            params.extend([start_date, end_date])

        # Order by score and limit
        sql_parts.append("ORDER BY raw_score DESC LIMIT ?")
        params.append(limit)

        sql = " ".join(sql_parts)

        rows = self._execute_query(sql, params)

        if not rows:
            return []

        # Normalize scores to [0, 1] range using min-max scaling
        # BM25 scores are negative (higher is better, closer to 0)
        raw_scores = [row["raw_score"] for row in rows]
        min_raw = min(raw_scores)
        max_raw = max(raw_scores)
        score_range = max_raw - min_raw if max_raw != min_raw else 1.0

        results = []
        for row in rows:
            # Normalize score to [0, 1]
            normalized_score = (
                (row["raw_score"] - min_raw) / score_range if score_range > 0 else 1.0
            )

            # Apply minimum score threshold
            if normalized_score < min_score:
                continue

            results.append(
                SearchResult(
                    id=row["id"],
                    content=row["content"],
                    score=normalized_score,
                    metadata={
                        "conversation_id": row["conversation_id"],
                        "role": row["role"],
                        "created_at": row["created_at"],
                    },
                    source_type="conversation",
                )
            )

        return results

    def delete_message(self, message_id: str) -> None:
        """Remove message from FTS index.
        
        Note: This is typically handled automatically by database triggers,
        but this method is provided for manual deletion if needed.
        
        Args:
            message_id: Unique message identifier to remove
        """
        self._execute_command(
            "DELETE FROM messages_fts WHERE message_id = ?", (message_id,)
        )

    def rebuild_index(self) -> None:
        """Rebuild FTS index from messages table.
        
        This is a maintenance operation that can be used to:
        - Recover from index corruption
        - Optimize index after many updates
        - Rebuild after schema changes
        """
        conn = self._connect()
        try:
            # Clear existing FTS index
            conn.execute("DELETE FROM messages_fts")
            
            # Repopulate from messages table
            conn.execute(
                """
                INSERT INTO messages_fts(message_id, content)
                SELECT id, content FROM messages
                """
            )
            
            # Optimize the FTS index
            conn.execute("INSERT INTO messages_fts(messages_fts) VALUES('optimize')")
            
            conn.commit()
        finally:
            conn.close()
