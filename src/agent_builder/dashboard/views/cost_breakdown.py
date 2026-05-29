"""Tab 3 — Cost breakdown (placeholder until F5.4)."""

from __future__ import annotations

from typing import Any

from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens


def build_cost_view(store: DashboardStore, tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    metrics = store.metrics()
    return ft.Container(
        expand=True,
        padding=16,
        bgcolor=tokens.surface,
        border_radius=8,
        content=ft.Column(
            [
                ft.Text("Cost breakdown", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(f"LLM calls: {metrics.llm_calls}", color=tokens.on_surface),
                ft.Text(f"Estimated cost: ${metrics.cost_usd:.4f}", color=tokens.on_surface),
                ft.Text("Charts and budget alerts ship in F5.4.", size=12, italic=True),
            ],
            expand=True,
        ),
    )
