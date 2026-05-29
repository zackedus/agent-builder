from pathlib import Path

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.tester import TesterAgent as TestingAgent
from agent_builder.config import Settings
from agent_builder.core.state import PlanTask
from agent_builder.core.workspace import Workspace
from agent_builder.llm.router import LLMRouter


@pytest.fixture
def tester_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "ws")
    ws.ensure_layout()
    (ws.project_dir / "hello.py").write_text(
        '"""Module hello."""\n\ndef greet() -> str:\n    return "hi"\n',
        encoding="utf-8",
    )
    return ws


@pytest.fixture
def router() -> LLMRouter:
    return LLMRouter(Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True))


@pytest.mark.asyncio
async def test_tester_passes_clean_project(
    tester_workspace: Workspace,
    router: LLMRouter,
) -> None:
    agent = TestingAgent(router, tester_workspace)
    task = PlanTask(
        id="T1.1",
        title="Hello",
        type="logic",
        files_affected=["hello.py"],
        acceptance_criteria=["module imports"],
    )
    result = await agent.run(
        AgentContext(
            session_id="s1",
            task_id=task.id,
            extra={"plan_task": task},
        ),
    )
    assert result.success is True
    test_result = result.data["test_result"]
    assert test_result.is_passing()
    assert tester_workspace.test_result_path("T1.1").is_file()
