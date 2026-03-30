"""Anthropic provider for skill-refine."""

from __future__ import annotations

import os

from skill_refine.providers.base import BaseProvider, LLMResponse


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        self._model = model

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> LLMResponse:
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "anthropic package not installed. "
                "Run: pip install 'skill-refine[anthropic]'"
            ) from e

        client = anthropic.Anthropic()
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        text = response.content[0].text
        return LLMResponse(
            text=text,
            model=self._model,
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
        )

    def is_available(self) -> bool:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def model_id(self) -> str:
        return self._model
