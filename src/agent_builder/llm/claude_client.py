"""Anthropic Claude API client."""

from __future__ import annotations

from typing import Any

from agent_builder.config import Settings
from agent_builder.llm.exceptions import LLMNotConfiguredError, LLMProviderError
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage

try:
    from anthropic import AsyncAnthropic
except ImportError:  # pragma: no cover
    AsyncAnthropic = None


class ClaudeClient:
    """Async wrapper around the Anthropic Messages API."""

    provider_id = "anthropic"

    def __init__(
        self,
        settings: Settings,
        *,
        model: str,
        model_alias: str,
        max_tokens: int = 4096,
    ) -> None:
        self._settings = settings
        self.model_id = model
        self.model_alias = model_alias
        self._max_tokens = max_tokens
        self._client: Any = None
        if settings.anthropic_configured() and AsyncAnthropic is not None:
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    def healthy(self) -> bool:
        return self._client is not None

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if not self.healthy():
            raise LLMNotConfiguredError("Anthropic API key is not configured")

        api_messages = [
            {"role": m.role, "content": m.content} for m in messages if m.role != "system"
        ]
        system_prompt = system or _extract_system(messages)

        try:
            kwargs: dict[str, Any] = {
                "model": self.model_id,
                "max_tokens": max_tokens or self._max_tokens,
                "messages": api_messages,
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            response = await self._client.messages.create(**kwargs)
        except Exception as exc:
            raise LLMProviderError(f"Claude request failed: {exc}") from exc

        text = _extract_text(response)
        usage = LLMUsage(
            input_tokens=getattr(response.usage, "input_tokens", 0),
            output_tokens=getattr(response.usage, "output_tokens", 0),
        )
        return LLMResponse(
            text=text,
            model=self.model_alias,
            provider=self.provider_id,
            usage=usage,
        )


def _extract_system(messages: list[LLMMessage]) -> str | None:
    for message in messages:
        if message.role == "system":
            return message.content
    return None


def _extract_text(response: Any) -> str:
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    if not parts:
        raise LLMProviderError("Claude returned empty content")
    return "".join(parts)
