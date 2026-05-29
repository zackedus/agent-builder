"""LLM provider errors."""

from agent_builder.core.exceptions import AgentBuilderError


class LLMError(AgentBuilderError):
    """Base error for LLM operations."""


class LLMProviderError(LLMError):
    """Provider call failed or returned invalid data."""


class LLMNotConfiguredError(LLMError):
    """Required API key or host is missing."""
