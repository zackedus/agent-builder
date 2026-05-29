"""Unit tests for release artifact validation."""

from __future__ import annotations

from pathlib import Path

from agent_builder.core.workspace import Workspace
from agent_builder.validation.build_output import (
    assert_session_cost_under_budget,
    validate_release_artifacts,
    write_mock_build_report,
)
from agent_builder.validation.project_output import BuildMetricsSummary


def test_validate_release_artifacts_ok(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "rel_ws")
    ws.ensure_layout()
    (ws.project_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
    write_mock_build_report(ws, project_name="demo")

    outcome = validate_release_artifacts(ws)
    assert outcome.ok is True
    assert outcome.package_path is not None


def test_assert_session_cost_under_budget() -> None:
    summary = BuildMetricsSummary(
        total_llm_calls=3,
        total_cost_usd=2.5,
        elapsed_seconds=10,
        input_tokens=1000,
        output_tokens=500,
    )
    assert_session_cost_under_budget(summary, max_usd=15.0)
