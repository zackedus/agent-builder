"""E2E: calculator prompt → plan → code → validation (mocked LLM)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.agents.base import AgentResult
from agent_builder.agents.review_models import ReviewResult
from agent_builder.agents.test_models import TesterReport
from agent_builder.config import Settings
from agent_builder.core.event_bus import Event, EventBus, EventType
from agent_builder.core.orchestrator import Orchestrator
from agent_builder.core.state import OrchestratorState
from agent_builder.core.workspace import Workspace
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage, LLMResponse, LLMUsage, RouteRequest
from agent_builder.validation.project_output import (
    assert_calculator_output,
    summarize_metrics_from_events,
    validate_project_output,
)
from tests.e2e.fixtures.calculator_responses import (
    CALCULATOR_CODE_RESPONSE,
    CALCULATOR_PLAN_JSON,
    CALCULATOR_USER_PROMPT,
)


@pytest.fixture
def calc_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "calc_ws")
    ws.ensure_layout()
    return ws


@pytest.fixture
def calc_settings(calc_workspace: Workspace) -> Settings:
    return Settings(
        anthropic_api_key="sk-test",
        workspace_dir=calc_workspace.root,
        _env_file=None,
        _env_ignore=True,
    )


@pytest.fixture
def mock_llm_router(calc_settings: Settings, calc_workspace: Workspace) -> LLMRouter:
    event_bus = EventBus(events_store=calc_workspace.events_store())
    router = LLMRouter(
        calc_settings,
        event_bus=event_bus,
        session_id="pending",
    )

    async def fake_complete(
        request: RouteRequest,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if request.agent == "planner":
            text = CALCULATOR_PLAN_JSON
        else:
            text = CALCULATOR_CODE_RESPONSE
        response = LLMResponse(
            text=text,
            model="claude-sonnet-4-6",
            provider="anthropic",
            usage=LLMUsage(100, 200),
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


@pytest.mark.asyncio
async def test_calculator_build_e2e_mocked(
    calc_workspace: Workspace,
    calc_settings: Settings,
    mock_llm_router: LLMRouter,
) -> None:
    orch = Orchestrator(calc_workspace, settings=calc_settings)
    session = orch.start(CALCULATOR_USER_PROMPT)
    mock_llm_router._session_id = session.session_id  # noqa: SLF001

    passed_test = AgentResult(
        success=True,
        data={
            "test_result": TesterReport(
                task_id="T1.1",
                status="passed",
                static_checks={"ruff": "passed", "mypy": "passed"},
                smoke="passed",
            ),
        },
    )
    approved = AgentResult(
        success=True,
        data={
            "review": ReviewResult(
                task_id="T1.1",
                verdict="approved",
                summary="Calculator looks good.",
            ),
        },
    )
    with (
        patch.object(orch, "router", return_value=mock_llm_router),
        patch("agent_builder.agents.tester.TesterAgent.run", AsyncMock(return_value=passed_test)),
        patch("agent_builder.agents.reviewer.ReviewerAgent.run", AsyncMock(return_value=approved)),
    ):
        session = await orch.run_build_pipeline(auto_approve=True)

    assert session.current_state == OrchestratorState.DONE
    assert session.metrics.total_llm_calls >= 2
    assert (calc_workspace.project_dir / "calc.py").is_file()

    validation = await validate_project_output(
        calc_workspace.project_dir,
        run_args=["2", "+", "3"],
    )
    assert validation.syntax_ok
    assert validation.entry_script == "calc.py"
    assert validation.run_ok
    assert_calculator_output(validation.run_stdout, 5.0)

    events = calc_workspace.events_store().load_all()
    metrics = summarize_metrics_from_events(events, session)
    assert metrics.total_llm_calls >= 2
    assert metrics.total_cost_usd >= 0
    assert session.metrics.elapsed_seconds >= 0


def test_calculator_cli_e2e_mocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from typer.testing import CliRunner

    from agent_builder.cli import app

    workspace = tmp_path / "cli_calc"
    workspace.mkdir()
    monkeypatch.setenv("AGENT_BUILDER_WORKSPACE", str(workspace))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    runner = CliRunner()

    async def fake_complete(
        request: RouteRequest,
        messages: list[LLMMessage],
        **kwargs: object,
    ) -> LLMResponse:
        text = CALCULATOR_PLAN_JSON if request.agent == "planner" else CALCULATOR_CODE_RESPONSE
        return LLMResponse(
            text=text,
            model="claude-sonnet-4-6",
            provider="anthropic",
            usage=LLMUsage(50, 80),
        )

    passed_test = AgentResult(
        success=True,
        data={
            "test_result": TesterReport(
                task_id="T1.1",
                status="passed",
                static_checks={"ruff": "passed", "mypy": "passed"},
                smoke="passed",
            ),
        },
    )
    approved = AgentResult(
        success=True,
        data={
            "review": ReviewResult(
                task_id="T1.1",
                verdict="approved",
                summary="ok",
            ),
        },
    )
    with (
        patch(
            "agent_builder.llm.router.LLMRouter.complete",
            AsyncMock(side_effect=fake_complete),
        ),
        patch("agent_builder.agents.tester.TesterAgent.run", AsyncMock(return_value=passed_test)),
        patch(
            "agent_builder.agents.reviewer.ReviewerAgent.run",
            AsyncMock(return_value=approved),
        ),
    ):
        result = runner.invoke(app, ["run", CALCULATOR_USER_PROMPT])

    assert result.exit_code == 0, result.stdout
    assert "Build complete" in result.stdout
    assert (workspace / "project" / "calc.py").is_file()
