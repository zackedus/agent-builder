"""Filter task nodes for the dependency graph view."""

from __future__ import annotations

from agent_builder.core.state import TaskNode, TaskStatus
from agent_builder.dashboard.state.kanban_columns import (
    BLOCKED_STATUSES,
    DONE_STATUSES,
    WAITING_STATUSES,
)

STATUS_FILTER_ALL = "all"
STATUS_FILTER_PENDING = "pending"
STATUS_FILTER_RUNNING = "running"
STATUS_FILTER_BLOCKED = "blocked"
STATUS_FILTER_DONE = "done"

STATUS_FILTER_LABELS: tuple[tuple[str, str], ...] = (
    (STATUS_FILTER_ALL, "Semua status"),
    (STATUS_FILTER_PENDING, "Menunggu"),
    (STATUS_FILTER_RUNNING, "Sedang dikerjakan"),
    (STATUS_FILTER_BLOCKED, "Diblokir"),
    (STATUS_FILTER_DONE, "Selesai"),
)


def _matches_status(task: TaskNode, status_filter: str) -> bool:
    if status_filter == STATUS_FILTER_ALL:
        return True
    status = TaskStatus(task.status)
    if status_filter == STATUS_FILTER_PENDING:
        return status in WAITING_STATUSES
    if status_filter == STATUS_FILTER_RUNNING:
        return status == TaskStatus.RUNNING
    if status_filter == STATUS_FILTER_BLOCKED:
        return status in BLOCKED_STATUSES
    if status_filter == STATUS_FILTER_DONE:
        return status in DONE_STATUSES
    return status.value == status_filter


def filter_graph_tasks(
    tasks: list[TaskNode],
    *,
    status_filter: str = STATUS_FILTER_ALL,
    agent_filter: str = "all",
    show_completed: bool = True,
) -> list[TaskNode]:
    """Return tasks visible under dashboard graph filters."""
    visible: list[TaskNode] = []
    for task in tasks:
        if not show_completed and TaskStatus(task.status) in DONE_STATUSES:
            continue
        if not _matches_status(task, status_filter):
            continue
        if agent_filter != "all" and task.assigned_agent.lower() != agent_filter.lower():
            continue
        visible.append(task)

    visible_ids = {t.id for t in visible}
    trimmed: list[TaskNode] = []
    for task in visible:
        deps = [dep for dep in task.depends_on if dep in visible_ids]
        trimmed.append(task.model_copy(update={"depends_on": deps}))
    return trimmed


def unique_agents(tasks: list[TaskNode]) -> list[str]:
    agents = sorted({t.assigned_agent for t in tasks})
    return agents
