"""Integration tests for Planner agent (opt-in via env)."""

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.planner import PlannerAgent
from agent_builder.config import Settings, get_settings
from agent_builder.llm.router import LLMRouter

pytestmark = pytest.mark.integration


@pytest.fixture
def live_settings() -> Settings:
    settings = get_settings()
    if not settings.run_integration_tests:
        pytest.skip("Set AGENT_BUILDER_RUN_INTEGRATION_TESTS=true to run")
    if not settings.anthropic_configured():
        pytest.skip("ANTHROPIC_API_KEY required for planner integration tests")
    return settings


@pytest.mark.asyncio
async def test_planner_live_generates_valid_plan(live_settings: Settings) -> None:
    router = LLMRouter(live_settings)
    agent = PlannerAgent(router)
    result = await agent.run(
        AgentContext(
            session_id="integration-planner",
            user_prompt="Build a CLI calculator that adds two numbers from argv",
        ),
    )
    assert result.success is True
    plan = result.data["plan"]
    assert plan.project_name
    assert len(plan.tasks) >= 1
    assert plan.estimated_complexity in ("small", "medium", "large")
    assert isinstance(plan.risks, list)
