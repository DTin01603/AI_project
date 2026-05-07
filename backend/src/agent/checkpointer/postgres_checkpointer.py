import importlib
from typing import Any


async def get_postgres_checkpointer(connection_string: str | None) -> Any:
    """Create and return an async Postgres checkpointer instance."""
    if not connection_string:
        raise ValueError("POSTGRES_CONNECTION_STRING is required when LANGGRAPH_CHECKPOINTER=postgres")

    try:
        module = importlib.import_module("langgraph.checkpoint.postgres.aio")
        AsyncPostgresSaver = getattr(module, "AsyncPostgresSaver")
    except Exception as error:  # pragma: no cover
        raise RuntimeError(
            "Missing Postgres checkpointer dependency. Install langgraph-checkpoint-postgres and asyncpg."
        ) from error

    if hasattr(AsyncPostgresSaver, "from_conn_string"):
        return AsyncPostgresSaver.from_conn_string(connection_string)
    return AsyncPostgresSaver(connection_string)
