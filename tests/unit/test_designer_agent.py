"""Unit tests for Designer agent."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.designer import DesignerAgent
from agent_builder.config import Settings
from agent_builder.core.state import PlanTask
from agent_builder.core.workspace import Workspace
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage, RouteRequest
from tests.unit.fixtures.design_responses import FORM_DESIGN_JSON


@pytest.fixture
def design_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "design_ws")
    ws.ensure_layout()
    return ws


@pytest.fixture
def router() -> LLMRouter:
    return LLMRouter(Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True))


@pytest.mark.asyncio
async def test_designer_writes_design_json(
    design_workspace: Workspace,
    router: LLMRouter,
) -> None:
    agent = DesignerAgent(router, design_workspace)
    task = PlanTask(
        id="T2.1",
        title="Expense form UI",
        type="ui",
        acceptance_criteria=["User can enter amount and category"],
    )

    async def fake_complete(
        request: RouteRequest,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        assert request.agent == "designer"
        return LLMResponse(
            text=FORM_DESIGN_JSON,
            model="claude-sonnet-4-6",
            provider="anthropic",
            usage=LLMUsage(80, 120),
        )

    router.complete = fake_complete  # type: ignore[method-assign]

    result = await agent.run(
        AgentContext(
            session_id="s1",
            user_prompt="Expense tracker",
            task_id=task.id,
            extra={"plan_task": task},
        ),
    )

    assert result.success is True
    path = design_workspace.design_path("T2.1")
    assert path.is_file()
    assert "expense_form" in path.read_text(encoding="utf-8")
