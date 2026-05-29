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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_generate(*_args: object, **_kwargs: object) -> None:
        test_path = tester_workspace.project_dir / "tests" / "test_task_t1_1.py"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(
            'from hello import greet\n\ndef test_greet() -> None:\n    assert greet() == "hi"\n',
            encoding="utf-8",
        )
        return test_path

    monkeypatch.setattr(
        "agent_builder.agents.tester.generate_pytest_for_task",
        fake_generate,
    )
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
    assert test_result.generated_tests
    assert tester_workspace.test_result_path("T1.1").is_file()


@pytest.mark.asyncio
async def test_tester_calls_llm_generator_when_criteria_present(
    tester_workspace: Workspace,
    router: LLMRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    async def fake_generate(*_args: object, **_kwargs: object) -> Path:
        nonlocal called
        called = True
        test_path = tester_workspace.project_dir / "tests" / "test_task_t1_1.py"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(
            'from hello import greet\n\ndef test_greet() -> None:\n    assert greet() == "hi"\n',
            encoding="utf-8",
        )
        return test_path

    monkeypatch.setattr(
        "agent_builder.agents.tester.generate_pytest_for_task",
        fake_generate,
    )
    agent = TestingAgent(router, tester_workspace)
    task = PlanTask(
        id="T1.1",
        title="Hello",
        type="logic",
        files_affected=["hello.py"],
        acceptance_criteria=["greet returns hi"],
    )
    await agent.run(AgentContext(session_id="s1", task_id=task.id, extra={"plan_task": task}))
    assert called is True
