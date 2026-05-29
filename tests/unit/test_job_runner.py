"""Unit tests for dashboard job runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_builder.core.workspace import Workspace
from agent_builder.dashboard.services.job_runner import resume_build, start_new_build


@pytest.mark.asyncio
async def test_start_new_build_empty_prompt(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "ws")
    ws.ensure_layout()
    ok, msg = await start_new_build(ws, "   ")
    assert ok is False
    assert "kosong" in msg.lower()


@pytest.mark.asyncio
async def test_resume_build_no_session(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "empty")
    ws.ensure_layout()
    ok, msg = await resume_build(ws)
    assert ok is False
