"""Tab 1 — Kanban board (placeholder until F5.2)."""

from __future__ import annotations

from typing import Any

from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens


def build_kanban_view(store: DashboardStore, tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    tasks = store.session.tasks if store.session else []
    body: Any
    if not tasks and store.plan:
        summary = ", ".join(t.id for t in store.plan.tasks[:8]) or "—"
        body = ft.Text(
            f"Plan tasks: {summary}\n\nFull Kanban columns land in F5.2.",
            color=tokens.on_surface,
        )
    elif tasks:
        body = ft.Column(
            [ft.Text(f"{task.id}: {task.title} [{task.status}]", size=13) for task in tasks[:12]],
            scroll=ft.ScrollMode.AUTO,
        )
    else:
        body = ft.Text(
            "No tasks loaded. Run agent-builder run to start a session.",
            color=tokens.on_surface,
        )

    return ft.Container(
        expand=True,
        padding=16,
        bgcolor=tokens.surface,
        border_radius=8,
        content=ft.Column(
            [
                ft.Text("Kanban", size=18, weight=ft.FontWeight.BOLD),
                body,
            ],
            expand=True,
        ),
    )
