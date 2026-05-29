"""Base agent class with retry logic and prompt templates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agent_builder.core.workspace import Workspace
from agent_builder.llm.prompt_loader import load_and_render, load_template, render_prompt
from agent_builder.llm.router import OPUS_ALIAS, SONNET_ALIAS, LLMRouter
from agent_builder.llm.types import LLMMessage, LLMResponse, RouteRequest

# Maps task_type to stronger routing tier on final retry (ARCHITECTURE.md §4.4).
TASK_TYPE_ESCALATION: dict[str, str] = {
    "scaffold": "default",
    "default": "refactor",
    "logic": "refactor",
    "embedding": "default",
}


@dataclass
class AgentContext:
    """Input context for a single agent run."""

    session_id: str
    user_prompt: str = ""
    task_id: str | None = None
    task_title: str = ""
    task_type: str = "default"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Output from an agent execution attempt."""

    success: bool
    output: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    errors: list[str] = field(default_factory=list)
    last_model: str | None = None


class BaseAgent(ABC):
    """Abstract agent with LLM calls, validation, and retry escalation."""

    name: str = "agent"
    max_retries: int = 3

    def __init__(
        self,
        router: LLMRouter,
        workspace: Workspace | None = None,
    ) -> None:
        self.router = router
        self.workspace = workspace

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Perform one agent attempt (subclasses call ``complete_llm`` here)."""

    @abstractmethod
    def validate_result(self, result: AgentResult) -> bool:
        """Return True if *result* meets acceptance criteria."""

    def task_type_for_attempt(self, base_task_type: str, attempt: int) -> str:
        """Escalate task type on the final retry to reach a stronger model."""
        if attempt < self.max_retries:
            return base_task_type
        return TASK_TYPE_ESCALATION.get(base_task_type, "refactor")

    def load_prompt(self, template_name: str, **variables: str) -> str:
        return load_and_render(template_name, variables)

    def render_prompt_template(self, template_name: str, **variables: str) -> str:
        return render_prompt(load_template(template_name), variables)

    async def complete_llm(
        self,
        context: AgentContext,
        messages: list[LLMMessage],
        *,
        task_type: str | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        resolved_type = task_type or context.task_type
        return await self.router.complete(
            RouteRequest(agent=self.name, task_type=resolved_type),
            messages,
            system=system,
            max_tokens=max_tokens,
        )

    async def run(self, context: AgentContext) -> AgentResult:
        """Execute with retries, error feedback, and model escalation."""
        errors: list[str] = []
        last_result = AgentResult(success=False, output="", attempts=0, errors=errors)
        feedback = ""

        for attempt in range(1, self.max_retries + 1):
            attempt_context = AgentContext(
                session_id=context.session_id,
                user_prompt=context.user_prompt,
                task_id=context.task_id,
                task_title=context.task_title,
                task_type=self.task_type_for_attempt(context.task_type, attempt),
                extra={
                    **context.extra,
                    "attempt": attempt,
                    "feedback": feedback,
                },
            )
            try:
                result = await self.execute(attempt_context)
            except Exception as exc:
                result = AgentResult(
                    success=False,
                    output="",
                    errors=[str(exc)],
                    attempts=attempt,
                )

            result.attempts = attempt
            result.errors = list(errors)
            if result.errors and not result.success:
                result.errors.extend(errors)

            if self.validate_result(result):
                result.success = True
                result.errors = errors
                return result

            if result.output:
                error_msg = result.output
            elif result.errors:
                error_msg = result.errors[-1]
            else:
                error_msg = "Validation failed"
            errors.append(f"Attempt {attempt}: {error_msg}")
            feedback = "\n".join(errors)
            last_result = result

        last_result.success = False
        last_result.errors = errors
        last_result.attempts = self.max_retries
        return last_result

    def expected_model_tier_for_attempt(self, base_task_type: str, attempt: int) -> str:
        """Return expected pricing alias for tests (sonnet vs opus)."""
        escalated = self.task_type_for_attempt(base_task_type, attempt)
        if escalated == "refactor":
            return OPUS_ALIAS
        if base_task_type == "scaffold" and attempt < self.max_retries:
            return "ollama"
        return SONNET_ALIAS
