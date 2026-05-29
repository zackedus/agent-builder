"""Unit tests for project index file watcher."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_builder.indexing.watcher import ProjectIndexWatcher


def test_mark_path_queues_relative_py(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    module = project / "app.py"
    module.write_text("x = 1\n", encoding="utf-8")

    watcher = ProjectIndexWatcher(project)
    watcher.mark_path(module)
    assert watcher.drain_pending() == ["app.py"]


def test_mark_path_ignores_non_py(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    watcher = ProjectIndexWatcher(project)
    watcher.mark_path(project / "readme.md")
    assert watcher.drain_pending() == []


@pytest.mark.asyncio
async def test_flush_calls_indexer(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    watcher = ProjectIndexWatcher(project)
    watcher.mark_path(project / "a.py")
    (project / "a.py").write_text("a = 1\n", encoding="utf-8")

    indexer = MagicMock()
    indexer.index_project = AsyncMock(return_value=2)

    count = await watcher.flush(indexer)
    assert count == 2
    indexer.index_project.assert_awaited_once_with(paths=["a.py"])
