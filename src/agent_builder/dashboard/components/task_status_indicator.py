"""Task status spinner / label for Kanban cards."""

from __future__ import annotations

from typing import Any

from agent_builder.core.state import TaskNode, TaskStatus


def build_task_status_indicator(task: TaskNode, *, on_surface: str) -> Any:
    import flet as ft

    status = TaskStatus(task.status)
    if status == TaskStatus.RUNNING:
        return ft.Row(
            [
                ft.ProgressRing(width=14, height=14, stroke_width=2),
                ft.Text("Running", size=11, color=on_surface),
            ],
            spacing=6,
        )
    if status == TaskStatus.BLOCKED_BY_DEPENDENCY:
        label = "Menunggu dependensi"
        if task.blocker_reason:
            label = task.blocker_reason[:40]
        return ft.Text(label, size=11, color=on_surface, italic=True)
    if status in (
        TaskStatus.BLOCKED_RETRY_EXCEEDED,
        TaskStatus.BLOCKED_NEEDS_INPUT,
        TaskStatus.FAILED_UNRECOVERABLE,
    ):
        label = task.blocker_reason or status.value.replace("_", " ")
        return ft.Text(label, size=11, color="#DC2626")
    if status == TaskStatus.DONE:
        return ft.Text("Selesai", size=11, color="#059669")
    if status == TaskStatus.SKIPPED:
        return ft.Text("Skipped", size=11, color=on_surface, italic=True)
    return ft.Text("Pending", size=11, color=on_surface)
