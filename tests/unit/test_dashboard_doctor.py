"""Unit tests for dashboard doctor checks."""

from __future__ import annotations

from pathlib import Path

from agent_builder.core.workspace import Workspace
from agent_builder.dashboard.services.doctor import run_doctor_checks


def test_run_doctor_checks(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "ws")
    ws.ensure_layout()
    checks = run_doctor_checks(ws)
    assert len(checks) >= 4
    names = {c.name for c in checks}
    assert "Workspace" in names
