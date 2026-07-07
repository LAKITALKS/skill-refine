"""Thin LLM abstraction layer. All LLM calls in the project go through here."""

from __future__ import annotations

from skill_refine.llm.providers.base import BaseProvider, LLMResponse
from skill_refine.llm.providers.factory import auto_select_provider, get_provider


def call_llm(
    prompt: str,
    *,
    system: str = "",
    provider: BaseProvider | None = None,
    provider_name: str | None = None,
    max_tokens: int = 8192,
    temperature: float = 0.3,
) -> LLMResponse:
    """Send a prompt to an LLM provider and return the response.

    Either pass a provider instance or a provider_name to look up.
    If neither is given, auto-selects the first available provider.
    """
    if provider is None:
        if provider_name:
            provider = get_provider(provider_name)
        else:
            provider = auto_select_provider()
            if provider is None:
                raise RuntimeError(
                    "No LLM provider available. "
                    "Set ANTHROPIC_API_KEY or start Ollama."
                )

    return provider.complete(
        prompt,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
    )
