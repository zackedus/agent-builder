"""Coder loads design.json into prompt context."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.coder import CoderAgent
from agent_builder.config import Settings
from agent_builder.core.state import PlanTask
from agent_builder.core.workspace import Workspace
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage, RouteRequest
from tests.unit.fixtures.design_responses import FORM_DESIGN_JSON


@pytest.fixture
def coder_ws(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "coder_design_ws")
    ws.ensure_layout()
    design = json.loads(FORM_DESIGN_JSON)
    path = ws.design_path("T-ui")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(design, indent=2), encoding="utf-8")
    return ws


@pytest.mark.asyncio
async def test_coder_prompt_includes_design_spec(coder_ws: Workspace) -> None:
    router = LLMRouter(Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True))
    captured: list[str] = []

    async def fake_complete(
        request: RouteRequest,
        messages: list[LLMMessage],
        **kwargs: object,
    ) -> LLMResponse:
        captured.append(messages[-1].content)
        return LLMResponse(
            text='```python:main.py\nprint("ok")\n```',
            model="claude-sonnet-4-6",
            provider="anthropic",
            usage=LLMUsage(10, 20),
        )

    router.complete = fake_complete  # type: ignore[method-assign]
    agent = CoderAgent(router, coder_ws)
    task = PlanTask(id="T-ui", title="Form UI", type="ui", files_affected=["main.py"])

    await agent.run(
        AgentContext(
            session_id="s1",
            extra={"plan_task": task},
        ),
    )

    assert captured
    assert "UI design spec" in captured[0]
    assert "expense_form" in captured[0]
