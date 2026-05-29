"""Orchestrator re-index hooks."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.core.orchestrator import Orchestrator
from agent_builder.core.workspace import Workspace


@pytest.fixture
def orch_workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "reindex_ws")
    ws.ensure_layout()
    return ws


@pytest.mark.asyncio
async def test_reindex_files_delegates_to_indexer(orch_workspace: Workspace) -> None:
    orch = Orchestrator(orch_workspace)
    with patch.object(orch, "_indexer") as mock_indexer_factory:
        indexer = AsyncMock()
        indexer.index_project = AsyncMock(return_value=3)
        mock_indexer_factory.return_value = indexer

        count = await orch.reindex_files(["hello.py", "utils.py"])

    assert count == 3
    indexer.index_project.assert_awaited_once_with(paths=["hello.py", "utils.py"])


@pytest.mark.asyncio
async def test_run_build_pipeline_stops_watcher(orch_workspace: Workspace) -> None:
    orch = Orchestrator(orch_workspace)
    orch.start("test app")
    orch.dispatch(
        __import__(
            "agent_builder.core.orchestrator",
            fromlist=["OrchestratorEvent"],
        ).OrchestratorEvent.PLAN_VALID,
    )

    with (
        patch.object(orch, "start_index_watcher") as start_w,
        patch.object(orch, "stop_index_watcher", AsyncMock()) as stop_w,
        patch.object(orch, "_run_build_loop", AsyncMock(return_value=orch.session)),
    ):
        await orch.run_build_pipeline(auto_approve=False)

    start_w.assert_called_once()
    stop_w.assert_awaited_once()
