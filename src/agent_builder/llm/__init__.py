"""LLM clients, router, and cost tracking."""

from agent_builder.llm.claude_client import ClaudeClient
from agent_builder.llm.cost_tracker import PRICING, CostRecord, CostTracker, estimate_cost
from agent_builder.llm.exceptions import LLMError, LLMNotConfiguredError, LLMProviderError
from agent_builder.llm.ollama_client import OllamaClient
from agent_builder.llm.prompt_loader import (
    PromptNotFoundError,
    PromptRenderError,
    list_templates,
    load_and_render,
    load_template,
    render_prompt,
)
from agent_builder.llm.router import (
    OLLAMA_ALIAS,
    OPUS_ALIAS,
    SONNET_ALIAS,
    LLMRouter,
    RouteDecision,
)
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage, RouteRequest

__all__ = [
    "ClaudeClient",
    "CostRecord",
    "CostTracker",
    "LLMError",
    "LLMMessage",
    "LLMNotConfiguredError",
    "LLMProviderError",
    "LLMResponse",
    "LLMRouter",
    "LLMUsage",
    "OllamaClient",
    "OPUS_ALIAS",
    "PromptNotFoundError",
    "PromptRenderError",
    "OLLAMA_ALIAS",
    "PRICING",
    "RouteDecision",
    "RouteRequest",
    "SONNET_ALIAS",
    "estimate_cost",
    "list_templates",
    "load_and_render",
    "load_template",
    "render_prompt",
]
