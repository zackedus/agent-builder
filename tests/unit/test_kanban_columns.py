"""Unit tests for Kanban column grouping."""

from __future__ import annotations

from agent_builder.core.state import TaskNode, TaskStatus
from agent_builder.dashboard.state.kanban_columns import KANBAN_COLUMNS, group_tasks_by_column


def test_group_tasks_by_column() -> None:
    tasks = [
        TaskNode(id="a", title="A", assigned_agent="coder", status=TaskStatus.PENDING),
        TaskNode(id="b", title="B", assigned_agent="coder", status=TaskStatus.RUNNING),
        TaskNode(
            id="c",
            title="C",
            assigned_agent="coder",
            status=TaskStatus.BLOCKED_NEEDS_INPUT,
        ),
        TaskNode(id="d", title="D", assigned_agent="coder", status=TaskStatus.DONE),
    ]
    grouped = group_tasks_by_column(tasks)
    assert [t.id for t in grouped["waiting"]] == ["a"]
    assert [t.id for t in grouped["running"]] == ["b"]
    assert [t.id for t in grouped["blocked"]] == ["c"]
    assert [t.id for t in grouped["done"]] == ["d"]
    assert len(KANBAN_COLUMNS) == 4
