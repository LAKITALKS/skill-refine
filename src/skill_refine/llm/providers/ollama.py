"""Ollama provider for the optional LLM layer (local models).

Importing this module requires ``httpx`` (part of the ``[llm]`` / ``[ollama]``
extras). The lint core never imports it.
"""

from __future__ import annotations

import httpx

from skill_refine.llm.providers.base import BaseProvider, LLMResponse


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(
        self,
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            resp = httpx.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=120.0,
            )
            resp.raise_for_status()
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self._base_url}. "
                "Is Ollama running? Start it with: ollama serve"
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama returned HTTP {e.response.status_code}: {e.response.text}"
            ) from e

        data = resp.json()
        text = data.get("message", {}).get("content", "")
        return LLMResponse(
            text=text,
            model=self._model,
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
        )

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=3.0)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def model_id(self) -> str:
        return self._model
