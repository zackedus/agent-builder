"""Kanban column definitions and grouping."""

from __future__ import annotations

from dataclasses import dataclass

from agent_builder.core.state import TaskNode, TaskStatus

WAITING_STATUSES = frozenset({TaskStatus.PENDING, TaskStatus.BLOCKED_BY_DEPENDENCY})
RUNNING_STATUSES = frozenset({TaskStatus.RUNNING})
BLOCKED_STATUSES = frozenset(
    {
        TaskStatus.BLOCKED_RETRY_EXCEEDED,
        TaskStatus.BLOCKED_NEEDS_INPUT,
        TaskStatus.FAILED_UNRECOVERABLE,
    }
)
DONE_STATUSES = frozenset({TaskStatus.DONE, TaskStatus.SKIPPED})


@dataclass(frozen=True)
class KanbanColumn:
    key: str
    title: str
    statuses: frozenset[TaskStatus]


KANBAN_COLUMNS: tuple[KanbanColumn, ...] = (
    KanbanColumn("waiting", "Menunggu", WAITING_STATUSES),
    KanbanColumn("running", "Sedang dikerjakan", RUNNING_STATUSES),
    KanbanColumn("blocked", "Diblokir", BLOCKED_STATUSES),
    KanbanColumn("done", "Selesai", DONE_STATUSES),
)


def group_tasks_by_column(tasks: list[TaskNode]) -> dict[str, list[TaskNode]]:
    """Map column key → tasks in that column."""
    grouped: dict[str, list[TaskNode]] = {col.key: [] for col in KANBAN_COLUMNS}
    for task in tasks:
        status = TaskStatus(task.status)
        placed = False
        for column in KANBAN_COLUMNS:
            if status in column.statuses:
                grouped[column.key].append(task)
                placed = True
                break
        if not placed:
            grouped["waiting"].append(task)
    return grouped
