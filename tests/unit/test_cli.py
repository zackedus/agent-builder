from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_builder.agents.plan_parser import parse_plan
from agent_builder.cli import app
from agent_builder.core.orchestrator import Orchestrator


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("AGENT_BUILDER_WORKSPACE", str(workspace))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    return workspace


MOCK_PLAN_JSON = """
{
  "project_name": "mock_app",
  "description": "Mock plan for CLI tests",
  "tasks": [{
    "id": "T1.1", "title": "Setup", "type": "scaffold",
    "acceptance_criteria": ["ok"]
  }],
  "estimated_complexity": "small",
  "risks": ["none"]
}
"""


@pytest.fixture(autouse=True)
def mock_build_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_builder.core.orchestrator import (
        OrchestratorEvent,
        TransitionContext,
        walk_happy_path,
    )
    from agent_builder.core.state import Plan, SessionState

    plan: Plan = parse_plan(MOCK_PLAN_JSON)

    async def fake_run_build_pipeline(
        self: Orchestrator,
        *,
        auto_approve: bool = True,
    ) -> SessionState:
        if self.session is None:
            raise RuntimeError("no session")
        if self.session.current_state.value == "PLANNING":
            self.dispatch(OrchestratorEvent.PLAN_VALID, TransitionContext(plan=plan))
        walk_happy_path(self, skip_planning=True)
        assert self.session is not None
        return self.session

    monkeypatch.setattr(Orchestrator, "run_build_pipeline", fake_run_build_pipeline)


def test_cli_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "agent-builder" in result.stdout.lower() or "Autonomous" in result.stdout


def test_version_command(runner: CliRunner) -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_doctor_command(runner: CliRunner) -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Anthropic" in result.stdout


def test_status_command(runner: CliRunner, cli_env: Path) -> None:
    run = runner.invoke(app, ["run", "Status test"])
    assert run.exit_code == 0
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "DONE" in result.stdout
    assert "Status test" in result.stdout


def test_status_session_id_mismatch(runner: CliRunner, cli_env: Path) -> None:
    runner.invoke(app, ["run", "x"])
    result = runner.invoke(app, ["status", "wrong-session-id"])
    assert result.exit_code == 1


def test_resume_terminal_session(runner: CliRunner, cli_env: Path) -> None:
    runner.invoke(app, ["run", "done test"])

    result = runner.invoke(app, ["resume"])
    assert result.exit_code == 1
    assert "terminal" in result.stdout.lower() or "DONE" in result.stdout
