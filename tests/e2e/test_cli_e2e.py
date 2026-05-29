"""E2E smoke tests for the CLI (no real LLM calls)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_builder.agents.plan_parser import parse_plan
from agent_builder.cli import app
from agent_builder.core.event_bus import EventType
from agent_builder.core.orchestrator import (
    Orchestrator,
    OrchestratorEvent,
    TransitionContext,
    walk_happy_path,
)
from agent_builder.core.state import Plan, SessionState


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


MOCK_PLAN_JSON = """
{
  "project_name": "mock_app",
  "description": "Mock plan",
  "tasks": [{"id": "T1.1", "title": "Setup", "type": "scaffold", "acceptance_criteria": ["ok"]}],
  "estimated_complexity": "small",
  "risks": []
}
"""


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("AGENT_BUILDER_WORKSPACE", str(workspace))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    monkeypatch.setenv("AGENT_BUILDER_RUN_INTEGRATION_TESTS", "false")
    return workspace


@pytest.fixture(autouse=True)
def mock_build_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
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
        self.finalize_session_metrics()
        assert self.session is not None
        return self.session

    monkeypatch.setattr(Orchestrator, "run_build_pipeline", fake_run_build_pipeline)


def test_e2e_run_creates_state_and_events(runner: CliRunner, cli_env: Path) -> None:
    result = runner.invoke(app, ["run", "Build a simple todo app"])
    assert result.exit_code == 0, result.stdout
    assert "Session started" in result.stdout or "Session ID" in result.stdout

    state_path = cli_env / ".agent" / "state.json"
    assert state_path.is_file()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_state"] == "DONE"
    assert state["user_prompt"] == "Build a simple todo app"
    session_id = state["session_id"]

    events_path = cli_env / ".agent" / "events.jsonl"
    assert events_path.is_file()
    lines = [line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 1
    first_event = json.loads(lines[0])
    assert first_event["type"] == EventType.STATE_CHANGED.value

    status_result = runner.invoke(app, ["status", session_id])
    assert status_result.exit_code == 0
    assert session_id in status_result.stdout
    assert "DONE" in status_result.stdout


def test_e2e_resume_terminal_after_done(runner: CliRunner, cli_env: Path) -> None:
    run_result = runner.invoke(app, ["run", "Resume test app"])
    assert run_result.exit_code == 0

    resume_result = runner.invoke(app, ["resume"])
    assert resume_result.exit_code == 1
    assert "terminal" in resume_result.stdout.lower()


def test_e2e_status_without_session_fails(runner: CliRunner, cli_env: Path) -> None:
    cli_env.mkdir(parents=True, exist_ok=True)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 1


def test_e2e_run_requires_api_key(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_BUILDER_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(app, ["run", "test"])
    assert result.exit_code == 1
