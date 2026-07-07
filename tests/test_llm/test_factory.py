"""Tests for the provider factory (requires the LLM extra: httpx)."""

from __future__ import annotations

import pytest

pytest.importorskip("httpx", reason="LLM extra not installed")

from skill_refine.llm.providers.factory import (
    auto_select_provider,
    get_provider,
    list_providers,
)


def test_list_providers() -> None:
    providers = list_providers()
    assert {"stub", "anthropic", "ollama"} <= set(providers)


def test_get_stub_provider() -> None:
    provider = get_provider("stub")
    assert provider.name == "stub"
    assert provider.is_available()


def test_stub_provider_complete() -> None:
    response = get_provider("stub").complete("Hello")
    assert response.text == "Hello"
    assert response.model == "stub"


def test_unknown_provider_raises() -> None:
    with pytest.raises(RuntimeError, match="nonexistent"):
        get_provider("nonexistent")


def test_auto_select_excludes_stub_by_default() -> None:
    # The stub echoes input and must never be auto-selected (that would fake a
    # result). Depending on the environment this is None or a real provider,
    # but it is never the stub.
    provider = auto_select_provider()
    assert provider is None or provider.name != "stub"


def test_auto_select_can_include_stub_as_last_resort() -> None:
    # With include_stub=True the stub is always available as a fallback, so a
    # provider is always returned.
    provider = auto_select_provider(include_stub=True)
    assert provider is not None
