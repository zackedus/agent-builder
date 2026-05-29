"""Live E2E: calculator prompt with real LLM (opt-in)."""

from pathlib import Path

import pytest

from agent_builder.config import Settings, get_settings
from agent_builder.core.orchestrator import Orchestrator
from agent_builder.core.state import OrchestratorState
from agent_builder.core.workspace import Workspace
from agent_builder.validation.project_output import (
    assert_calculator_output,
    summarize_metrics_from_events,
    validate_project_output,
)
from tests.e2e.fixtures.calculator_responses import CALCULATOR_USER_PROMPT

pytestmark = pytest.mark.integration


@pytest.fixture
def live_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    if not get_settings().run_integration_tests:
        pytest.skip("Set AGENT_BUILDER_RUN_INTEGRATION_TESTS=true to run")
    if not get_settings().anthropic_configured():
        pytest.skip("ANTHROPIC_API_KEY required")
    ws = tmp_path / "live_calc"
    monkeypatch.setenv("AGENT_BUILDER_WORKSPACE", str(ws))
    return get_settings()


@pytest.mark.asyncio
async def test_calculator_live_build(live_settings: Settings) -> None:
    workspace = Workspace(live_settings.workspace_dir)
    workspace.ensure_layout()
    orch = Orchestrator(workspace, settings=live_settings)
    orch.start(CALCULATOR_USER_PROMPT)

    session = await orch.run_build_pipeline(auto_approve=True)
    assert session.current_state == OrchestratorState.DONE

    validation = await validate_project_output(
        workspace.project_dir,
        run_args=["2", "+", "3"],
    )
    assert validation.syntax_ok, validation.syntax_errors
    assert validation.run_ok, validation.run_stderr
    assert_calculator_output(validation.run_stdout, 5.0)

    events = workspace.events_store().load_all()
    metrics = summarize_metrics_from_events(events, session)
    assert metrics.total_llm_calls >= 2
    assert metrics.total_cost_usd < 1.0, f"Cost too high: ${metrics.total_cost_usd}"
