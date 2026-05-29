"""Unit tests for DevOps agent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_builder.agents.base import AgentContext
from agent_builder.agents.devops import DevOpsAgent
from agent_builder.config import Settings
from agent_builder.core.state import Plan, PlanTask, TechStack
from agent_builder.core.workspace import Workspace
from agent_builder.llm.router import LLMRouter


@pytest.fixture
def devops_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "devops_ws")
    ws.ensure_layout()
    (ws.project_dir / "main.py").write_text(
        "import flet\n\ndef main():\n    pass\n",
        encoding="utf-8",
    )
    plan = Plan(
        project_name="todo-app",
        description="Todo app",
        tech_stack=TechStack(gui="flet", storage="sqlite"),
        tasks=[
            PlanTask(id="T1.1", title="Todo CRUD", type="logic", acceptance_criteria=[]),
        ],
    )
    ws.save_plan(plan)
    return ws


@pytest.fixture
def router() -> LLMRouter:
    return LLMRouter(Settings(anthropic_api_key="sk-test", _env_file=None, _env_ignore=True))


@pytest.mark.asyncio
async def test_devops_agent_creates_release_without_pyinstaller(
    devops_workspace: Workspace,
    router: LLMRouter,
) -> None:
    agent = DevOpsAgent(router, devops_workspace)
    plan = devops_workspace.load_plan()
    result = await agent.run(
        AgentContext(
            session_id="s-devops",
            user_prompt="Build todo",
            extra={"plan": plan},
        ),
    )

    assert result.success is True
    report = result.data["build_report"]
    assert report.package_path is not None
    assert report.status in ("partial", "success")
    assert (devops_workspace.dist_dir / "BUILD_REPORT.json").is_file()
    zip_files = list(devops_workspace.dist_dir.glob("*.zip"))
    assert zip_files

    build_json = json.loads(
        (devops_workspace.dist_dir / "BUILD_REPORT.json").read_text(encoding="utf-8"),
    )
    assert build_json["project_name"] == "todo-app"
