import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LangGraphSettings:
    """Runtime settings for LangGraph v2 execution.

    Attributes:
        checkpointer: Backend type for checkpoint persistence ("sqlite" or "postgres").
        db_path: SQLite file path used when checkpointer is sqlite.
        postgres_connection_string: DSN used when checkpointer is postgres.
    """

    checkpointer: str = os.getenv("LANGGRAPH_CHECKPOINTER", "sqlite").strip().lower()
    db_path: str = os.getenv("LANGGRAPH_DB_PATH", "./checkpoints.db")
    postgres_connection_string: str | None = os.getenv("POSTGRES_CONNECTION_STRING")


langgraph_settings = LangGraphSettings()


async def get_checkpointer() -> Any:
    """Return an initialized LangGraph checkpointer based on environment settings."""
    backend = langgraph_settings.checkpointer

    if backend == "postgres":
        from research_agent.checkpointer.postgres_checkpointer import get_postgres_checkpointer

        return await get_postgres_checkpointer(langgraph_settings.postgres_connection_string)

    from research_agent.checkpointer.sqlite_checkpointer import get_sqlite_checkpointer

    return await get_sqlite_checkpointer(langgraph_settings.db_path)
