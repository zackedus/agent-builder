"""Unit tests for LLM pytest generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.test_generator import (
    collect_source_context,
    generate_pytest_for_task,
    task_test_relpath,
)
from agent_builder.config import Settings
from agent_builder.core.state import PlanTask
from agent_builder.core.workspace import Workspace
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage, RouteRequest

MOCK_PYTEST_RESPONSE = '''
```python:tests/test_task_t1_1.py
"""Generated tests for hello module."""
from hello import greet


def test_greet_returns_hi() -> None:
    assert greet() == "hi"
```
'''


@pytest.fixture
def gen_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "gen_ws")
    ws.ensure_layout()
    (ws.project_dir / "hello.py").write_text(
        '"""Hello."""\n\ndef greet() -> str:\n    return "hi"\n',
        encoding="utf-8",
    )
    return ws


@pytest.fixture
def gen_router() -> LLMRouter:
    return LLMRouter(Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True))


def test_task_test_relpath_sanitizes_id() -> None:
    assert task_test_relpath("T1.1") == "tests/test_task_t1_1.py"
    assert task_test_relpath("T-9/x") == "tests/test_task_t_9_x.py"


def test_collect_source_context_reads_affected_files(gen_workspace: Workspace) -> None:
    task = PlanTask(
        id="T1.1",
        title="Hello",
        type="logic",
        files_affected=["hello.py"],
        acceptance_criteria=["greet works"],
    )
    text = collect_source_context(gen_workspace, task)
    assert "hello.py" in text
    assert "def greet" in text


@pytest.mark.asyncio
async def test_generate_pytest_writes_file(
    gen_workspace: Workspace,
    gen_router: LLMRouter,
) -> None:
    task = PlanTask(
        id="T1.1",
        title="Hello module",
        type="logic",
        files_affected=["hello.py"],
        acceptance_criteria=["greet returns hi"],
    )
    context = AgentContext(session_id="s1", user_prompt="Build hello")

    async def fake_complete(
        request: RouteRequest,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        assert request.agent == "tester"
        return LLMResponse(
            text=MOCK_PYTEST_RESPONSE,
            model="claude-sonnet-4-6",
            provider="anthropic",
            usage=LLMUsage(50, 100),
        )

    gen_router.complete = fake_complete  # type: ignore[method-assign]

    path = await generate_pytest_for_task(gen_router, gen_workspace, context, task)
    assert path is not None
    assert path.name == "test_task_t1_1.py"
    content = path.read_text(encoding="utf-8")
    assert "test_greet_returns_hi" in content

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(path), "-q"],
        cwd=gen_workspace.project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.asyncio
async def test_generate_skips_without_criteria(
    gen_workspace: Workspace,
    gen_router: LLMRouter,
) -> None:
    task = PlanTask(id="T2", title="Empty", type="logic", acceptance_criteria=[])
    context = AgentContext(session_id="s1")
    path = await generate_pytest_for_task(gen_router, gen_workspace, context, task)
    assert path is None
