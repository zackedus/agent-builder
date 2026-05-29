"""Sandbox execution errors."""

from agent_builder.core.exceptions import AgentBuilderError


class SandboxError(AgentBuilderError):
    """Base error for sandbox operations."""


class SandboxSecurityError(SandboxError):
    """Code failed static security checks."""


class SandboxExecutionError(SandboxError):
    """Command execution failed or timed out."""


class SandboxPathError(SandboxError):
    """Path is outside the allowed workspace."""
