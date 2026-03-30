"""Provider factory for skill-refine."""

from __future__ import annotations

from skill_refine.providers.base import BaseProvider

_REGISTRY: dict[str, type[BaseProvider]] = {}


def register_provider(name: str, cls: type[BaseProvider]) -> None:
    _REGISTRY[name] = cls


def get_provider(name: str, **kwargs: object) -> BaseProvider:
    """Get a provider instance by name.

    Raises RuntimeError with a helpful message if the provider is unknown
    or not available.
    """
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys())) or "(none)"
        raise RuntimeError(
            f"Unknown provider '{name}'. Available: {available}"
        )

    provider = _REGISTRY[name](**kwargs)  # type: ignore[arg-type]

    if not provider.is_available():
        hints = {
            "anthropic": "Set ANTHROPIC_API_KEY or run: pip install 'skill-refine[anthropic]'",
            "ollama": "Start Ollama with: ollama serve",
        }
        hint = hints.get(name, "Check provider configuration.")
        raise RuntimeError(
            f"Provider '{name}' is not available. {hint}"
        )

    return provider


def list_providers() -> list[str]:
    return sorted(_REGISTRY.keys())


def auto_select_provider() -> BaseProvider | None:
    """Try to find a working provider automatically.

    Priority: anthropic > ollama > stub.
    """
    for name in ["anthropic", "ollama", "stub"]:
        if name not in _REGISTRY:
            continue
        try:
            provider = _REGISTRY[name]()
            if provider.is_available():
                return provider
        except Exception:
            continue
    return None


# Register built-in providers
def _register_builtins() -> None:
    from skill_refine.providers.anthropic import AnthropicProvider
    from skill_refine.providers.ollama import OllamaProvider
    from skill_refine.providers.stub import StubProvider

    register_provider("anthropic", AnthropicProvider)
    register_provider("ollama", OllamaProvider)
    register_provider("stub", StubProvider)


_register_builtins()
