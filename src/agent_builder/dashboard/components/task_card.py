"""Kanban task card."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent_builder.core.state import TaskNode, TaskStatus
from agent_builder.dashboard.components.agent_tag import build_agent_tag
from agent_builder.dashboard.components.task_status_indicator import build_task_status_indicator
from agent_builder.dashboard.flet_ui import border_all
from agent_builder.dashboard.theme import DashboardThemeTokens


def build_task_card(
    task: TaskNode,
    tokens: DashboardThemeTokens,
    *,
    on_click: Callable[[str], None] | None = None,
    selected: bool = False,
) -> Any:
    import flet as ft

    status = TaskStatus(task.status)
    border_left = None
    if status == TaskStatus.RUNNING:
        border_left = ft.Border(left=ft.BorderSide(3, tokens.primary))
    elif status in (
        TaskStatus.BLOCKED_RETRY_EXCEEDED,
        TaskStatus.BLOCKED_NEEDS_INPUT,
        TaskStatus.FAILED_UNRECOVERABLE,
    ):
        border_left = ft.Border(left=ft.BorderSide(3, "#DC2626"))

    def handle_click(_: Any) -> None:
        if on_click is not None:
            on_click(task.id)

    return ft.Container(
        on_click=handle_click,
        border=border_left or border_all(1, tokens.border),
        border_radius=8,
        padding=10,
        margin=ft.Margin.only(bottom=8),
        bgcolor=tokens.surface_variant if selected else tokens.surface,
        content=ft.Column(
            [
                ft.Text(
                    task.id,
                    size=10,
                    font_family="Consolas",
                    color=tokens.on_surface,
                    opacity=0.6,
                ),
                ft.Text(task.title, size=13, color=tokens.on_surface),
                ft.Row(
                    [
                        build_agent_tag(task.assigned_agent),
                        build_task_status_indicator(task, on_surface=tokens.on_surface),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=4,
        ),
    )
