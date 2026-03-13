"""Pytest configuration for RAG property tests."""

import pytest


# Disable pytest-asyncio for property tests to avoid collection issues
def pytest_configure(config):
    """Configure pytest for property tests."""
    config.option.asyncio_mode = "auto"
