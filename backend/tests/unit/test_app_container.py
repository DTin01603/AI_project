"""Unit tests for AppContainer (step 7a of refactor-architecture).

Covers tasks.md tests for step 7:
- 7.1: same SQLiteConnectionFactory shared across services
- 7.2: run_migrations called exactly once when container initialized
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import api.deps as deps_module
from api.deps import AppContainer, get_container


@pytest.fixture(autouse=True)
def _clear_container_cache():
    get_container.cache_clear()
    yield
    get_container.cache_clear()


def test_should_share_single_factory_across_services_when_container_initialized(
    tmp_path: Path,
) -> None:
    container = AppContainer(db_path=str(tmp_path / "container.db"))

    assert container.conversation_service._factory is container.factory
    assert container.citation_service._factory is container.factory
    assert container.conversation_repo._factory is container.factory
    assert container.message_repo._factory is container.factory


def test_should_run_migrations_exactly_once_when_container_initialized(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "migrations.db")

    with patch.object(
        deps_module, "run_migrations", wraps=deps_module.run_migrations
    ) as spy:
        AppContainer(db_path=db_path)

    assert spy.call_count == 1
    args, _ = spy.call_args
    assert args[0].db_path == db_path
