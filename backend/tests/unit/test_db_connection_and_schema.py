"""Unit tests for db.connection.SQLiteConnectionFactory and db.schema.run_migrations.

Covers task 1 of the refactor-architecture plan:
- Test 1.1: factory sets all required PRAGMAs on every connection.
- Test 1.2: transaction() rolls back when the with-block raises.
- Test 1.3: run_migrations is idempotent (re-running yields the same schema).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db.connection import SQLiteConnectionFactory
from db.schema import run_migrations


def test_should_set_all_pragmas_when_connect(tmp_path: Path) -> None:
    factory = SQLiteConnectionFactory(str(tmp_path / "pragma.db"))

    with factory.connect() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        row_factory = conn.row_factory

    assert journal_mode.lower() == "wal"
    assert synchronous == 1  # NORMAL
    assert busy_timeout == 5000
    assert row_factory is sqlite3.Row


def test_should_rollback_when_transaction_raises(tmp_path: Path) -> None:
    factory = SQLiteConnectionFactory(str(tmp_path / "rollback.db"))

    # Arrange: create a table and seed one row OUTSIDE the failing transaction.
    with factory.connect() as conn:
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.execute("INSERT INTO t (id) VALUES (?)", (0,))

    # Act: insert a second row inside a transaction, then raise.
    with pytest.raises(RuntimeError, match="boom"):
        with factory.transaction() as conn:
            conn.execute("INSERT INTO t (id) VALUES (?)", (1,))
            raise RuntimeError("boom")

    # Assert: only the seed row survived; the in-transaction row was rolled back.
    with factory.connect() as conn:
        rows = conn.execute("SELECT id FROM t ORDER BY id").fetchall()

    assert [row[0] for row in rows] == [0]


def test_should_be_idempotent_when_run_migrations_called_twice(tmp_path: Path) -> None:
    factory = SQLiteConnectionFactory(str(tmp_path / "migrations.db"))

    run_migrations(factory)
    with factory.connect() as conn:
        first_objects = {
            (row["type"], row["name"])
            for row in conn.execute(
                "SELECT type, name FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' AND name NOT LIKE 'messages_fts_%'"
            ).fetchall()
        }

    # Act: re-run migrations — must not raise.
    run_migrations(factory)

    with factory.connect() as conn:
        second_objects = {
            (row["type"], row["name"])
            for row in conn.execute(
                "SELECT type, name FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' AND name NOT LIKE 'messages_fts_%'"
            ).fetchall()
        }

    assert first_objects == second_objects
    # Sanity check: core tables present.
    table_names = {name for kind, name in first_objects if kind == "table"}
    assert {"conversations", "messages", "citations", "citation_usage", "documents"} <= table_names


def test_should_create_parent_dir_when_db_path_nested(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "deeper" / "x.db"
    assert not nested.parent.exists()

    factory = SQLiteConnectionFactory(str(nested))
    with factory.connect() as conn:
        conn.execute("CREATE TABLE probe (id INTEGER)")

    assert nested.parent.is_dir()
    assert nested.exists()
