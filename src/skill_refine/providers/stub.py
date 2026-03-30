"""Stub provider for testing and fallback."""

from __future__ import annotations

import re

from skill_refine.providers.base import BaseProvider, LLMResponse

# Match the skill content block in the rewrite prompt
_SKILL_BLOCK_RE = re.compile(
    r"## Original skill file\s*\n(.*?)\n## Instructions",
    re.DOTALL,
)


class StubProvider(BaseProvider):
    """Returns the original skill content unchanged.

    Useful for testing the pipeline end-to-end without LLM costs.
    Extracts the skill file from the prompt if possible, otherwise echoes.
    """

    name = "stub"

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> LLMResponse:
        match = _SKILL_BLOCK_RE.search(prompt)
        if match:
            text = match.group(1).strip() + "\n"
        else:
            text = prompt
        return LLMResponse(text=text, model="stub")

    def is_available(self) -> bool:
        return True

    def model_id(self) -> str:
        return "stub"
