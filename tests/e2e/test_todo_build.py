"""E2E F3.4: Flet todo + SQLite prompt with self-correction loop (mocked LLM)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.agents.base import AgentContext, AgentResult
from agent_builder.agents.design_parser import parse_design
from agent_builder.agents.review_models import ReviewResult
from agent_builder.agents.test_models import TesterReport
from agent_builder.config import Settings
from agent_builder.core.event_bus import Event, EventBus, EventType
from agent_builder.core.orchestrator import Orchestrator
from agent_builder.core.state import OrchestratorState
from agent_builder.core.workspace import Workspace, atomic_write_json
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage, RouteRequest
from agent_builder.validation.project_output import (
    assert_flet_entrypoint,
    validate_project_output,
    validate_todo_crud,
)
from tests.e2e.fixtures.todo_responses import (
    TODO_CODE_V1,
    TODO_CODE_V2,
    TODO_PLAN_JSON,
    TODO_USER_PROMPT,
)
from tests.unit.fixtures.design_responses import LIST_DESIGN_JSON


@pytest.fixture
def todo_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "todo_ws")
    ws.ensure_layout()
    return ws


@pytest.fixture
def todo_settings(todo_workspace: Workspace) -> Settings:
    return Settings(
        anthropic_api_key="sk-test",
        workspace_dir=todo_workspace.root,
        _env_file=None,
        _env_ignore=True,
    )


@pytest.fixture
def mock_todo_llm_router(todo_settings: Settings, todo_workspace: Workspace) -> LLMRouter:
    event_bus = EventBus(events_store=todo_workspace.events_store())
    router = LLMRouter(
        todo_settings,
        event_bus=event_bus,
        session_id="pending",
    )
    coder_calls = 0

    async def fake_complete(
        request: RouteRequest,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        nonlocal coder_calls
        if request.agent == "planner":
            text = TODO_PLAN_JSON
        elif request.agent == "coder":
            coder_calls += 1
            text = TODO_CODE_V1 if coder_calls == 1 else TODO_CODE_V2
        else:
            text = "{}"
        response = LLMResponse(
            text=text,
            model="claude-sonnet-4-6",
            provider="anthropic",
            usage=LLMUsage(120, 240),
        )
        await event_bus.publish(
            Event(
                type=EventType.LLM_CALL,
                session_id=router._session_id or "",
                payload={
                    "agent": request.agent,
                    "model": response.model,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "coder_attempt": coder_calls if request.agent == "coder" else None,
                },
            )
        )
        return response

    router.complete = fake_complete  # type: ignore[method-assign]
    router._coder_calls = lambda: coder_calls  # type: ignore[attr-defined]
    return router


def _make_tester_side_effect(workspace: Workspace) -> AsyncMock:
    calls = 0

    async def fake_tester_run(*args: object, **kwargs: object) -> AgentResult:
        nonlocal calls
        calls += 1
        context = args[-1]
        assert isinstance(context, AgentContext)
        task_id = context.task_id or "T1.1"
        if calls == 1:
            report = TesterReport(
                task_id=task_id,
                status="failed",
                static_checks={"ruff": "passed", "mypy": "passed"},
                smoke="passed",
            )
            atomic_write_json(
                workspace.test_result_path(task_id),
                report.model_dump(mode="json"),
            )
            return AgentResult(
                success=False,
                output="status=failed; CRUD add/list mismatch",
                data={"test_result": report},
            )
        report = TesterReport(
            task_id=task_id,
            status="passed",
            static_checks={"ruff": "passed", "mypy": "passed"},
            smoke="passed",
        )
        atomic_write_json(
            workspace.test_result_path(task_id),
            report.model_dump(mode="json"),
        )
        return AgentResult(success=True, data={"test_result": report})

    return AsyncMock(side_effect=fake_tester_run)


@pytest.mark.asyncio
async def test_todo_build_e2e_self_correction(
    todo_workspace: Workspace,
    todo_settings: Settings,
    mock_todo_llm_router: LLMRouter,
) -> None:
    """F3.4: todo prompt, retry after test failure, then CRUD + Flet entry validation."""
    orch = Orchestrator(todo_workspace, settings=todo_settings)
    session = orch.start(TODO_USER_PROMPT)
    mock_todo_llm_router._session_id = session.session_id  # noqa: SLF001

    approved = AgentResult(
        success=True,
        data={
            "review": ReviewResult(
                task_id="T1.1",
                verdict="approved",
                summary="Todo CRUD and Flet entry look good.",
            ),
        },
    )
    design_ok = AgentResult(
        success=True,
        data={
            "design": parse_design(LIST_DESIGN_JSON),
            "design_path": ".agent/designs/T1.1.json",
        },
    )

    with (
        patch.object(orch, "router", return_value=mock_todo_llm_router),
        patch("agent_builder.agents.designer.DesignerAgent.run", AsyncMock(return_value=design_ok)),
        patch(
            "agent_builder.agents.tester.TesterAgent.run",
            _make_tester_side_effect(todo_workspace),
        ),
        patch("agent_builder.agents.reviewer.ReviewerAgent.run", AsyncMock(return_value=approved)),
    ):
        session = await orch.run_build_pipeline(auto_approve=True)

    assert session.current_state == OrchestratorState.DONE
    assert session.get_task_retry_count("T1.1") >= 1

    persisted = todo_workspace.events_store().load_all()
    coder_llm_calls = sum(
        1 for e in persisted if e.type == EventType.LLM_CALL and e.payload.get("agent") == "coder"
    )
    assert coder_llm_calls >= 2
    assert todo_workspace.test_result_path("T1.1").is_file()

    project = todo_workspace.project_dir
    assert (project / "todo_store.py").is_file()
    assert (project / "main.py").is_file()

    syntax = await validate_project_output(project)
    assert syntax.syntax_ok
    assert syntax.entry_script == "main.py"

    assert_flet_entrypoint(project)

    crud = await validate_todo_crud(project)
    assert crud.steps_ok, crud.errors

    feedback = todo_workspace.test_result_path("T1.1").read_text(encoding="utf-8")
    assert "failed" in feedback
