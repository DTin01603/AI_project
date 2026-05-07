from typing import Any


async def get_sqlite_checkpointer(db_path: str = "./checkpoints.db") -> Any:
    """Create and return an async SQLite checkpointer instance."""
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except Exception as error:  # pragma: no cover
        raise RuntimeError(
            "Missing SQLite checkpointer dependency. Install langgraph-checkpoint-sqlite and aiosqlite."
        ) from error

    if hasattr(AsyncSqliteSaver, "from_conn_string"):
        return AsyncSqliteSaver.from_conn_string(db_path)
    return AsyncSqliteSaver(db_path)
