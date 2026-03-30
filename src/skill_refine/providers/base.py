"""Base provider interface for LLM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class BaseProvider(ABC):
    """Abstract base for all LLM providers."""

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Send a completion request and return the response."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and reachable."""

    def model_id(self) -> str:
        """Return the model identifier used by this provider."""
        return "unknown"
