"""Shared types for LLM clients and router."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    provider: str
    usage: LLMUsage = field(default_factory=LLMUsage)


@dataclass(frozen=True)
class RouteRequest:
    agent: str
    task_type: str = "default"
    context_size: int = 0
