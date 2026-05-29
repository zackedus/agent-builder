"""E2E F4.6: expense tracker prompt → release package + feature validation (mocked LLM)."""

from __future__ import annotations

from datetime import date
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
from agent_builder.validation.build_output import (
    assert_session_cost_under_budget,
    seed_mock_executable,
    validate_launchable_artifact,
    validate_release_artifacts,
    write_mock_build_report,
)
from agent_builder.validation.project_output import (
    assert_flet_entrypoint,
    summarize_metrics_from_events,
    validate_expense_features,
    validate_project_output,
)
from tests.e2e.fixtures.expense_responses import (
    EXPENSE_CODE_V1,
    EXPENSE_CODE_V2,
    EXPENSE_PLAN_JSON,
    EXPENSE_USER_PROMPT,
)
from tests.unit.fixtures.design_responses import FORM_DESIGN_JSON


@pytest.fixture
def expense_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "expense_ws")
    ws.ensure_layout()
    return ws


@pytest.fixture
def expense_settings(expense_workspace: Workspace) -> Settings:
    return Settings(
        anthropic_api_key="sk-test",
        workspace_dir=expense_workspace.root,
        sandbox_layer="subprocess",
        coder_use_index=False,
        _env_file=None,
        _env_ignore=True,
    )


@pytest.fixture
def mock_expense_llm_router(
    expense_settings: Settings,
    expense_workspace: Workspace,
) -> LLMRouter:
    event_bus = EventBus(events_store=expense_workspace.events_store())
    router = LLMRouter(
        expense_settings,
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
            text = EXPENSE_PLAN_JSON
        elif request.agent == "coder":
            coder_calls += 1
            text = EXPENSE_CODE_V1 if coder_calls == 1 else EXPENSE_CODE_V2
        else:
            text = "{}"
        response = LLMResponse(
            text=text,
            model="claude-sonnet-4-6",
            provider="anthropic",
            usage=LLMUsage(500, 800),
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
                },
            )
        )
        return response

    router.complete = fake_complete  # type: ignore[method-assign]
    return router


def _make_tester_pass(workspace: Workspace) -> AsyncMock:
    async def fake_tester_run(*args: object, **kwargs: object) -> AgentResult:
        context = args[-1]
        assert isinstance(context, AgentContext)
        task_id = context.task_id or "T1.1"
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


async def _fake_devops_run(*args: object, **kwargs: object) -> AgentResult:
    context = args[-1]
    assert isinstance(context, AgentContext)
    agent = args[0]
    workspace = agent.workspace
    assert workspace is not None
    launcher = seed_mock_executable(workspace, project_name="expense_tracker")
    artifact_rel = str(launcher.relative_to(workspace.project_dir)).replace("\\", "/")
    report = write_mock_build_report(
        workspace,
        project_name="expense_tracker",
        artifact_rel=artifact_rel,
    )
    return AgentResult(
        success=True,
        output=f"status={report.status}",
        data={"build_report": report},
    )


@pytest.mark.asyncio
async def test_expense_build_e2e_release_and_features(
    expense_workspace: Workspace,
    expense_settings: Settings,
    mock_expense_llm_router: LLMRouter,
) -> None:
    """F4.6: expense prompt, pipeline DONE, zip artifact, CLI features, cost budget."""
    orch = Orchestrator(expense_workspace, settings=expense_settings)
    session = orch.start(EXPENSE_USER_PROMPT)
    mock_expense_llm_router._session_id = session.session_id  # noqa: SLF001

    approved = AgentResult(
        success=True,
        data={
            "review": ReviewResult(
                task_id="T1.1",
                verdict="approved",
                summary="Expense tracker CRUD and chart look good.",
            ),
        },
    )
    design_ok = AgentResult(
        success=True,
        data={
            "design": parse_design(FORM_DESIGN_JSON),
            "design_path": ".agent/designs/T1.1.json",
        },
    )

    with (
        patch.object(orch, "router", return_value=mock_expense_llm_router),
        patch("agent_builder.agents.designer.DesignerAgent.run", AsyncMock(return_value=design_ok)),
        patch("agent_builder.agents.tester.TesterAgent.run", _make_tester_pass(expense_workspace)),
        patch("agent_builder.agents.reviewer.ReviewerAgent.run", AsyncMock(return_value=approved)),
        patch("agent_builder.agents.devops.DevOpsAgent.run", _fake_devops_run),
    ):
        session = await orch.run_build_pipeline(auto_approve=True)

    assert session.current_state == OrchestratorState.DONE

    project = expense_workspace.project_dir
    assert (project / "expense_store.py").is_file()
    assert (project / "chart_data.py").is_file()
    assert (project / "main.py").is_file()

    syntax = await validate_project_output(project)
    assert syntax.syntax_ok
    assert_flet_entrypoint(project)

    month = date.today().strftime("%Y-%m")
    features = await validate_expense_features(project, month=month)
    assert features.steps_ok, features.errors

    release = validate_release_artifacts(expense_workspace)
    assert release.ok, release.errors
    assert release.build_report is not None
    assert release.package_path is not None
    assert release.artifact_path is not None

    launch = await validate_launchable_artifact(project, release.artifact_path)
    assert launch.ok, launch.errors

    events = expense_workspace.events_store().load_all()
    summary = summarize_metrics_from_events(events, session)
    assert_session_cost_under_budget(summary, max_usd=15.0)
    assert summary.total_llm_calls >= 2
