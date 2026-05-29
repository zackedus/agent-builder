"""Dialog for resolving blocked tasks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent_builder.core.state import TaskNode


def build_blocker_dialog(
    task: TaskNode,
    *,
    on_skip: Callable[[], None],
    on_retry: Callable[[], None],
    on_cancel: Callable[[], None],
) -> Any:
    import flet as ft

    note = ft.TextField(
        label="Catatan / jawaban",
        multiline=True,
        min_lines=2,
        max_lines=4,
        value=task.blocker_reason or "",
    )

    return ft.AlertDialog(
        modal=True,
        title=ft.Text(f"Resolve blocker — {task.id}"),
        content=ft.Column(
            [
                ft.Text(task.title, size=14),
                note,
            ],
            tight=True,
            spacing=8,
        ),
        actions=[
            ft.TextButton("Batal", on_click=lambda _: on_cancel()),
            ft.TextButton("Skip task", on_click=lambda _: on_skip()),
            ft.ElevatedButton("Retry", on_click=lambda _: on_retry()),
        ],
    )
