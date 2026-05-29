"""Coder agent uses index search and SEARCH/REPLACE patches."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.coder import CoderAgent
from agent_builder.config import Settings
from agent_builder.core.state import Plan, PlanTask, TechStack
from agent_builder.core.workspace import Workspace
from agent_builder.indexing.chroma_store import SearchHit
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage, RouteRequest
from agent_builder.tools.file_ops import read_project_file, write_project_file


@pytest.fixture
def coder_ws(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "coder_idx_ws")
    ws.ensure_layout()
    write_project_file(
        ws,
        "store.py",
        "def get_items():\n    return []\n",
    )
    return ws


@pytest.mark.asyncio
async def test_coder_prompt_includes_index_hits(coder_ws: Workspace) -> None:
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
    hits = [
        SearchHit(
            chunk_id="c1",
            file_path="store.py",
            symbol="get_items",
            symbol_type="function",
            content="def get_items():\n    return []",
            score=0.91,
        ),
    ]

    agent = CoderAgent(router, coder_ws)
    plan = Plan(
        project_name="todo",
        description="Todo app",
        tech_stack=TechStack(),
        tasks=[PlanTask(id="T1.1", title="List items", type="logic", files_affected=["main.py"])],
    )
    task = plan.tasks[0]

    with patch(
        "agent_builder.agents.coder.fetch_index_hits",
        AsyncMock(return_value=hits),
    ):
        await agent.run(
            AgentContext(
                session_id="s1",
                user_prompt="Show todo list",
                extra={"plan": plan, "plan_task": task},
            ),
        )

    assert captured
    assert "Relevant code from project index" in captured[0]
    assert "store.py" in captured[0]
    assert "Existing project files" in captured[0]


@pytest.mark.asyncio
async def test_coder_applies_search_replace_patch(coder_ws: Workspace) -> None:
    router = LLMRouter(Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True))
    patch_response = """```python:store.py
<<<<<<< SEARCH
def get_items():
    return []
=======
def get_items():
    return ["todo"]
>>>>>>> REPLACE
```"""

    async def fake_complete(
        request: RouteRequest,
        messages: list[LLMMessage],
        **kwargs: object,
    ) -> LLMResponse:
        return LLMResponse(
            text=patch_response,
            model="claude-sonnet-4-6",
            provider="anthropic",
            usage=LLMUsage(10, 20),
        )

    router.complete = fake_complete  # type: ignore[method-assign]
    no_index = Settings(
        anthropic_api_key="sk-test",
        coder_use_index=False,
        _env_file=None,
        _env_ignore=True,
    )
    agent = CoderAgent(router, coder_ws, settings=no_index)
    task = PlanTask(id="T1.1", title="Update store", type="logic", files_affected=["store.py"])

    result = await agent.run(
        AgentContext(
            session_id="s1",
            extra={"plan_task": task},
        ),
    )

    assert result.success is True
    content = read_project_file(coder_ws, "store.py")
    assert 'return ["todo"]' in content
