from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.coder import CoderAgent
from agent_builder.config import Settings
from agent_builder.core.state import Plan, PlanTask, TechStack
from agent_builder.core.workspace import Workspace
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMResponse, LLMUsage
from agent_builder.tools.file_ops import read_project_file


@pytest.fixture
def settings() -> Settings:
    return Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True)


@pytest.fixture
def router(settings: Settings) -> LLMRouter:
    return LLMRouter(settings)


@pytest.fixture
def coder_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "ws")
    ws.ensure_layout()
    return ws


SAMPLE_CODE_RESPONSE = """```python:calc.py
def add(a: float, b: float) -> float:
    return a + b

if __name__ == "__main__":
    print(add(1, 2))
```"""


@pytest.mark.asyncio
async def test_coder_writes_files(router: LLMRouter, coder_workspace: Workspace) -> None:
    agent = CoderAgent(router, coder_workspace)
    plan = Plan(
        project_name="calc",
        description="CLI calculator",
        tech_stack=TechStack(),
        tasks=[
            PlanTask(
                id="T1.1",
                title="Calculator",
                type="logic",
                files_affected=["calc.py"],
                acceptance_criteria=["Runs"],
            )
        ],
    )
    task = plan.tasks[0]

    with patch.object(
        router,
        "complete",
        AsyncMock(
            return_value=LLMResponse(
                text=SAMPLE_CODE_RESPONSE,
                model="claude-sonnet",
                provider="anthropic",
                usage=LLMUsage(10, 20),
            )
        ),
    ):
        result = await agent.run(
            AgentContext(
                session_id="s1",
                user_prompt="Build calculator",
                task_id=task.id,
                task_title=task.title,
                task_type=task.type,
                extra={"plan": plan, "plan_task": task},
            ),
        )

    assert result.success is True
    assert "calc.py" in result.data["files"]
    assert "def add" in read_project_file(coder_workspace, "calc.py")


@pytest.mark.asyncio
async def test_coder_rejects_invalid_syntax(router: LLMRouter, coder_workspace: Workspace) -> None:
    agent = CoderAgent(router, coder_workspace)
    bad = """```python:bad.py
def oops(
```"""
    with patch.object(
        router,
        "complete",
        AsyncMock(
            return_value=LLMResponse(
                text=bad,
                model="m",
                provider="anthropic",
                usage=LLMUsage(1, 1),
            )
        ),
    ):
        result = await agent.run(
            AgentContext(session_id="s1", user_prompt="x", extra={}),
        )
    assert result.success is False
