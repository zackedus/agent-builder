"""Ollama local LLM client."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

from agent_builder.config import Settings
from agent_builder.llm.exceptions import LLMProviderError
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage

try:
    from ollama import AsyncClient
except ImportError:  # pragma: no cover
    AsyncClient = None


class OllamaClient:
    """Async chat client for Ollama."""

    provider_id = "ollama"

    def __init__(
        self,
        settings: Settings,
        *,
        model: str | None = None,
        model_alias: str = "ollama",
    ) -> None:
        self._settings = settings
        self.model_id = model or settings.ollama_model_coder
        self.model_alias = model_alias
        self._host = settings.ollama_host.rstrip("/")
        self._client: Any = None
        if AsyncClient is not None:
            self._client = AsyncClient(host=self._host)

    def healthy(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return bool(resp.status == 200)
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if self._client is None:
            raise LLMProviderError("Ollama client is not available")

        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        options: dict[str, Any] = {}
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        try:
            kwargs: dict[str, Any] = {
                "model": self.model_id,
                "messages": api_messages,
            }
            if system:
                kwargs["system"] = system
            elif _extract_system(messages):
                kwargs["system"] = _extract_system(messages)
            if options:
                kwargs["options"] = options
            response = await self._client.chat(**kwargs)
        except Exception as exc:
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc

        if isinstance(response, dict):
            message = response.get("message")
        else:
            message = getattr(response, "message", None)
        text = ""
        if isinstance(message, dict):
            text = str(message.get("content", ""))
        elif message is not None:
            text = str(getattr(message, "content", ""))

        if not text.strip():
            raise LLMProviderError("Ollama returned empty content")

        prompt_tokens = _get_eval_count(response, "prompt_eval_count")
        output_tokens = _get_eval_count(response, "eval_count")
        return LLMResponse(
            text=text,
            model=self.model_alias,
            provider=self.provider_id,
            usage=LLMUsage(input_tokens=prompt_tokens, output_tokens=output_tokens),
        )


def _extract_system(messages: list[LLMMessage]) -> str | None:
    for message in messages:
        if message.role == "system":
            return message.content
    return None


def _get_eval_count(response: Any, key: str) -> int:
    if isinstance(response, dict):
        return int(response.get(key, 0) or 0)
    return int(getattr(response, key, 0) or 0)
