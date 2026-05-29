"""Tab 1 — Kanban board with four columns."""

from __future__ import annotations

from typing import Any

from agent_builder.core.state import TaskNode, TaskStatus
from agent_builder.dashboard.components.blocker_dialog import build_blocker_dialog
from agent_builder.dashboard.components.task_card import build_task_card
from agent_builder.dashboard.components.task_detail_drawer import build_task_detail_drawer
from agent_builder.dashboard.state.kanban_columns import KANBAN_COLUMNS, group_tasks_by_column
from agent_builder.dashboard.state.kanban_tasks import resolve_kanban_tasks
from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens

_BLOCKER_STATUSES = frozenset(
    {
        TaskStatus.BLOCKED_RETRY_EXCEEDED,
        TaskStatus.BLOCKED_NEEDS_INPUT,
        TaskStatus.FAILED_UNRECOVERABLE,
    }
)


def _close_blocker_dialog(ui_page: Any, dialog: Any) -> None:
    if hasattr(ui_page, "close"):
        ui_page.close(dialog)
    elif hasattr(ui_page, "dialog"):
        ui_page.dialog = None
        ui_page.update()


def build_kanban_view(
    store: DashboardStore,
    tokens: DashboardThemeTokens,
    page: Any | None = None,
) -> Any:
    import flet as ft

    tasks = resolve_kanban_tasks(store.session_for_views(), store.plan)
    grouped = group_tasks_by_column(tasks)
    selected_id = store.selected_task_id
    selected_task = next((t for t in tasks if t.id == selected_id), None)

    def select_task(task_id: str) -> None:
        store.select_task(task_id if task_id != selected_id else None)

    def close_drawer() -> None:
        store.select_task(None)

    def open_blocker_dialog(task: TaskNode) -> None:
        if page is None:
            return
        ui_page = page
        dialog_holder: list[Any] = []

        def close_dialog() -> None:
            if dialog_holder:
                _close_blocker_dialog(ui_page, dialog_holder[0])

        dialog = build_blocker_dialog(
            task,
            on_skip=close_dialog,
            on_retry=close_dialog,
            on_cancel=close_dialog,
        )
        dialog_holder.append(dialog)
        if hasattr(ui_page, "open"):
            ui_page.open(dialog)
        else:
            ui_page.dialog = dialog
            ui_page.update()

    columns: list[Any] = []
    for column in KANBAN_COLUMNS:
        column_tasks = grouped[column.key]
        cards = [
            build_task_card(
                task,
                tokens,
                on_click=select_task,
                selected=task.id == selected_id,
            )
            for task in column_tasks
        ]
        columns.append(
            ft.Container(
                expand=True,
                bgcolor=tokens.surface_variant,
                border_radius=8,
                padding=10,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(column.title, weight=ft.FontWeight.W_600, size=14),
                                ft.Container(
                                    content=ft.Text(str(len(column_tasks)), size=11),
                                    bgcolor=tokens.border,
                                    border_radius=10,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Column(cards, scroll=ft.ScrollMode.AUTO, expand=True, spacing=0),
                    ],
                    expand=True,
                    spacing=8,
                ),
            )
        )

    board = ft.Row(columns, expand=True, spacing=12, vertical_alignment=ft.CrossAxisAlignment.START)

    drawer: Any | None = None
    if selected_task is not None:
        show_resolve = TaskStatus(selected_task.status) in _BLOCKER_STATUSES
        drawer = build_task_detail_drawer(
            selected_task,
            tokens,
            store.plan,
            on_close=close_drawer,
            on_resolve_blocker=(
                (lambda: open_blocker_dialog(selected_task)) if show_resolve else None
            ),
            visible=True,
        )

    if drawer is not None:
        return ft.Stack(
            [
                ft.Container(content=board, expand=True, padding=ft.padding.only(right=8)),
                ft.Container(
                    content=drawer,
                    right=0,
                    top=0,
                    bottom=0,
                    width=360,
                ),
            ],
            expand=True,
        )

    return ft.Container(
        expand=True,
        padding=8,
        content=board,
    )
