"""Tests for the provider factory (requires the LLM extra: httpx)."""

from __future__ import annotations

import pytest

pytest.importorskip("httpx", reason="LLM extra not installed")

from skill_refine.llm.providers.factory import get_provider, list_providers


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
