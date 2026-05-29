from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
from agent_builder.config import Settings
from agent_builder.llm.router import OLLAMA_ALIAS, OPUS_ALIAS, SONNET_ALIAS, LLMRouter
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage, RouteRequest


class FlakyAgent(BaseAgent):
    """Fails validation twice, succeeds on third attempt."""

    name = "coder"

    def __init__(self, router: LLMRouter) -> None:
        super().__init__(router)
        self.validate_calls = 0
        self.execute_calls = 0

    async def execute(self, context: AgentContext) -> AgentResult:
        self.execute_calls += 1
        response = await self.complete_llm(
            context,
            [LLMMessage(role="user", content=f"attempt {context.extra.get('attempt')}")],
        )
        return AgentResult(
            success=False,
            output=response.text,
            last_model=response.model,
        )

    def validate_result(self, result: AgentResult) -> bool:
        self.validate_calls += 1
        return self.validate_calls >= 3


class AlwaysFailAgent(BaseAgent):
    name = "tester"

    async def execute(self, context: AgentContext) -> AgentResult:
        return AgentResult(success=False, output="bad")

    def validate_result(self, result: AgentResult) -> bool:
        return False


@pytest.fixture
def settings() -> Settings:
    return Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True)


@pytest.fixture
def router(settings: Settings) -> LLMRouter:
    return LLMRouter(settings)


@pytest.mark.asyncio
async def test_retry_budget_max_three_attempts(router: LLMRouter) -> None:
    agent = AlwaysFailAgent(router)
    result = await agent.run(AgentContext(session_id="s", user_prompt="test"))
    assert result.success is False
    assert result.attempts == 3
    assert len(result.errors) == 3


@pytest.mark.asyncio
async def test_retry_succeeds_on_third_attempt(router: LLMRouter) -> None:
    agent = FlakyAgent(router)
    with patch.object(
        router,
        "complete",
        AsyncMock(
            return_value=LLMResponse(
                text="ok",
                model=SONNET_ALIAS,
                provider="anthropic",
                usage=LLMUsage(1, 1),
            )
        ),
    ):
        result = await agent.run(
            AgentContext(session_id="s", user_prompt="app", task_type="scaffold"),
        )
    assert result.success is True
    assert result.attempts == 3
    assert agent.execute_calls == 3


@pytest.mark.asyncio
async def test_retry_escalates_task_type_on_final_attempt(router: LLMRouter) -> None:
    agent = FlakyAgent(router)
    captured: list[RouteRequest] = []

    async def track_complete(
        request: RouteRequest,
        messages: list[LLMMessage],
        **kwargs: object,
    ) -> LLMResponse:
        captured.append(request)
        return LLMResponse(
            text="x",
            model=SONNET_ALIAS,
            provider="anthropic",
            usage=LLMUsage(1, 1),
        )

    with patch.object(router, "complete", side_effect=track_complete):
        await agent.run(
            AgentContext(session_id="s", user_prompt="app", task_type="scaffold"),
        )

    assert len(captured) == 3
    assert captured[0].task_type == "scaffold"
    assert captured[1].task_type == "scaffold"
    assert captured[2].task_type == "default"


def test_task_type_escalation_refactor_uses_opus_tier(router: LLMRouter) -> None:
    agent = FlakyAgent(router)
    assert agent.task_type_for_attempt("logic", 3) == "refactor"
    assert agent.expected_model_tier_for_attempt("logic", 3) == OPUS_ALIAS
    assert agent.expected_model_tier_for_attempt("scaffold", 1) == OLLAMA_ALIAS


def test_load_prompt_helper(router: LLMRouter) -> None:
    agent = FlakyAgent(router)
    text = agent.load_prompt(
        "coder",
        task_id="T1",
        task_title="Setup",
        task_type="scaffold",
        user_prompt="Todo",
        context="none",
        files_affected="main.py",
    )
    assert "T1" in text
