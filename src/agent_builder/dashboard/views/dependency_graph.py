"""Tab 2 — Dependency graph (placeholder until F5.3)."""

from __future__ import annotations

from typing import Any

from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens


def build_dependency_view(store: DashboardStore, tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    plan = store.plan
    edges = []
    if plan:
        for task in plan.tasks:
            for dep in task.depends_on:
                edges.append(f"{dep} → {task.id}")

    detail = "\n".join(edges[:20]) if edges else "No plan dependencies yet."
    return ft.Container(
        expand=True,
        padding=16,
        bgcolor=tokens.surface,
        border_radius=8,
        content=ft.Column(
            [
                ft.Text("Dependency graph", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(detail, color=tokens.on_surface),
                ft.Text("DAG canvas ships in F5.3.", size=12, italic=True),
            ],
            expand=True,
        ),
    )
