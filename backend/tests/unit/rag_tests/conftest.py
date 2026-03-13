"""Pytest configuration for RAG unit tests."""


def pytest_configure(config):
    """Configure pytest for RAG tests."""
    config.option.asyncio_mode = "auto"