from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.planner import PlannerAgent
from agent_builder.config import Settings
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMResponse, LLMUsage

VALID_PLAN_JSON = """
{
  "project_name": "todo_app",
  "description": "Todo list desktop app",
  "tech_stack": {"gui": "flet", "storage": "sqlite"},
  "milestones": [{"id": "M1", "name": "Setup", "tasks": ["T1.1"]}],
  "tasks": [
    {
      "id": "T1.1",
      "title": "Scaffold project",
      "type": "scaffold",
      "depends_on": [],
      "files_affected": ["main.py"],
      "acceptance_criteria": ["App launches"]
    }
  ],
  "estimated_complexity": "small",
  "risks": ["SQLite schema migrations"]
}
"""


@pytest.fixture
def settings() -> Settings:
    return Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True)


@pytest.fixture
def router(settings: Settings) -> LLMRouter:
    return LLMRouter(settings)


@pytest.mark.asyncio
async def test_planner_parses_valid_json(router: LLMRouter) -> None:
    agent = PlannerAgent(router)
    with patch.object(
        router,
        "complete",
        AsyncMock(
            return_value=LLMResponse(
                text=f"```json\n{VALID_PLAN_JSON}\n```",
                model="claude-sonnet",
                provider="anthropic",
                usage=LLMUsage(10, 20),
            )
        ),
    ):
        result = await agent.run(
            AgentContext(session_id="sess-1", user_prompt="Build a todo app"),
        )

    assert result.success is True
    plan = result.data["plan"]
    assert plan.project_name == "todo_app"
    assert len(plan.tasks) == 1


@pytest.mark.asyncio
async def test_planner_retries_on_malformed_json(router: LLMRouter) -> None:
    agent = PlannerAgent(router)
    responses = [
        LLMResponse(text="not json at all", model="m", provider="anthropic", usage=LLMUsage(1, 1)),
        LLMResponse(
            text=VALID_PLAN_JSON,
            model="m",
            provider="anthropic",
            usage=LLMUsage(1, 1),
        ),
    ]
    with patch.object(router, "complete", AsyncMock(side_effect=responses)):
        result = await agent.run(
            AgentContext(session_id="sess-1", user_prompt="Build a todo app"),
        )

    assert result.success is True
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_planner_max_retries(router: LLMRouter) -> None:
    agent = PlannerAgent(router)
    with patch.object(
        router,
        "complete",
        AsyncMock(
            return_value=LLMResponse(
                text="garbage",
                model="m",
                provider="anthropic",
                usage=LLMUsage(1, 1),
            )
        ),
    ):
        result = await agent.run(
            AgentContext(session_id="sess-1", user_prompt="Build app"),
        )

    assert result.success is False
    assert result.attempts == agent.max_retries
