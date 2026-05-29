"""Slide-in task detail panel for Kanban."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent_builder.core.state import Plan, PlanTask, TaskNode
from agent_builder.dashboard.components.agent_tag import build_agent_tag
from agent_builder.dashboard.flet_ui import border_all
from agent_builder.dashboard.theme import DashboardThemeTokens


def _plan_task_for(plan: Plan | None, task_id: str) -> PlanTask | None:
    if plan is None:
        return None
    for task in plan.tasks:
        if task.id == task_id:
            return task
    return None


def build_task_detail_drawer(
    task: TaskNode,
    tokens: DashboardThemeTokens,
    plan: Plan | None,
    *,
    on_close: Callable[[], None],
    on_resolve_blocker: Callable[[], None] | None = None,
    visible: bool = True,
) -> Any:
    import flet as ft

    plan_task = _plan_task_for(plan, task.id)
    criteria = plan_task.acceptance_criteria if plan_task else []
    files = plan_task.files_affected if plan_task else []

    actions: list[Any] = [
        ft.TextButton("Tutup", on_click=lambda _: on_close()),
    ]
    if on_resolve_blocker is not None:
        actions.insert(
            0,
            ft.ElevatedButton("Resolve blocker", on_click=lambda _: on_resolve_blocker()),
        )

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(task.title, size=18, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(ft.Icons.CLOSE, on_click=lambda _: on_close()),
                ],
            ),
            build_agent_tag(task.assigned_agent),
            ft.Text(f"Status: {task.status}", size=13, color=tokens.on_surface),
            ft.Text(f"Retries: {task.retry_count}", size=12, color=tokens.on_surface),
            ft.Divider(),
            ft.Text("Acceptance criteria", size=13, weight=ft.FontWeight.W_600),
            ft.Column(
                [ft.Text(f"• {item}", size=12) for item in criteria] or [ft.Text("—", size=12)],
                spacing=4,
            ),
            ft.Text("Files affected", size=13, weight=ft.FontWeight.W_600),
            ft.Text(", ".join(files) if files else "—", size=12),
            ft.Divider(),
            ft.Row(actions, alignment=ft.MainAxisAlignment.END),
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Container(
        width=360 if visible else 0,
        visible=visible,
        bgcolor=tokens.surface,
        border=border_all(1, tokens.border),
        padding=16,
        right=0,
        top=0,
        bottom=0,
        content=content,
    )
