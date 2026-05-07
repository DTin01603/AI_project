"""Tests for the lazy LLM adapter registry (Task 8 of improve-architecture-v2).

The registry must:
- Not import any vendor SDK at module load time.
- Provide a `list_providers()` helper that doesn't trigger SDK imports.
- Surface a clear error when resolving an adapter for an uninstalled SDK.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest


def test_should_import_adapters_module_without_optional_sdk() -> None:
    """Importing `adapters` and listing providers must not need any SDK."""
    # Force a fresh import to exercise module load.
    sys.modules.pop("adapters", None)
    sys.modules.pop("adapters.google_adapter", None)
    sys.modules.pop("adapters.groq_adapter", None)

    import adapters  # noqa: F401

    providers = adapters.list_providers()
    assert "groq" in providers
    assert "gemini" in providers

    # Vendor SDK modules must not have been imported as a side effect.
    assert "adapters.google_adapter" not in sys.modules
    assert "adapters.groq_adapter" not in sys.modules


def test_should_raise_clear_error_when_resolving_adapter_for_uninstalled_provider() -> None:
    """If the SDK fails to import, get_adapter_for_model must surface ImportError."""
    import adapters

    sys.modules.pop("adapters.groq_adapter", None)

    def fake_import(name, *args, **kwargs):
        if name == "adapters.groq_adapter":
            raise ImportError("No module named 'groq'")
        import importlib
        return importlib.__import__(name, *args, **kwargs)

    with patch("adapters.importlib.import_module") as mock_import:
        mock_import.side_effect = lambda name: (
            (_ for _ in ()).throw(ImportError("No module named 'groq'"))
            if name == "adapters.groq_adapter"
            else __import__(name)
        )
        with pytest.raises(ImportError, match="groq"):
            adapters.get_adapter_for_model("groq/llama-3.3-70b-versatile")


def test_should_raise_value_error_for_unknown_provider() -> None:
    import adapters

    with pytest.raises(ValueError, match="unsupported model provider"):
        adapters.get_adapter_for_model("anthropic/claude-3-5-sonnet")
