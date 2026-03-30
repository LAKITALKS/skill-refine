"""Tests for provider factory."""

from skill_refine.providers.factory import list_providers, get_provider


def test_list_providers() -> None:
    providers = list_providers()
    assert "stub" in providers
    assert "anthropic" in providers
    assert "ollama" in providers


def test_get_stub_provider() -> None:
    provider = get_provider("stub")
    assert provider.name == "stub"
    assert provider.is_available()


def test_stub_provider_complete() -> None:
    provider = get_provider("stub")
    response = provider.complete("Hello")
    assert response.text == "Hello"
    assert response.model == "stub"


def test_unknown_provider_raises() -> None:
    try:
        get_provider("nonexistent")
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "nonexistent" in str(e)
