"""Unit tests for dependency graph filters."""

from __future__ import annotations

from agent_builder.core.state import TaskNode, TaskStatus
from agent_builder.dashboard.graph.filters import (
    STATUS_FILTER_RUNNING,
    filter_graph_tasks,
    unique_agents,
)


def test_filter_graph_tasks_hides_completed() -> None:
    tasks = [
        TaskNode(id="a", title="A", assigned_agent="coder", status=TaskStatus.DONE),
        TaskNode(id="b", title="B", assigned_agent="coder", status=TaskStatus.PENDING),
    ]
    visible = filter_graph_tasks(tasks, show_completed=False)
    assert [t.id for t in visible] == ["b"]


def test_filter_graph_tasks_by_status_and_agent() -> None:
    tasks = [
        TaskNode(id="a", title="A", assigned_agent="coder", status=TaskStatus.RUNNING),
        TaskNode(id="b", title="B", assigned_agent="designer", status=TaskStatus.PENDING),
    ]
    running = filter_graph_tasks(tasks, status_filter=STATUS_FILTER_RUNNING)
    assert [t.id for t in running] == ["a"]
    designers = filter_graph_tasks(tasks, agent_filter="designer")
    assert [t.id for t in designers] == ["b"]


def test_filter_graph_tasks_trims_dependencies() -> None:
    tasks = [
        TaskNode(id="a", title="A", assigned_agent="coder", status=TaskStatus.DONE),
        TaskNode(
            id="b",
            title="B",
            assigned_agent="coder",
            status=TaskStatus.PENDING,
            depends_on=["a"],
        ),
    ]
    visible = filter_graph_tasks(tasks, show_completed=False)
    assert len(visible) == 1
    assert visible[0].depends_on == []


def test_unique_agents_sorted() -> None:
    tasks = [
        TaskNode(id="1", title="x", assigned_agent="coder"),
        TaskNode(id="2", title="y", assigned_agent="designer"),
        TaskNode(id="3", title="z", assigned_agent="coder"),
    ]
    assert unique_agents(tasks) == ["coder", "designer"]
