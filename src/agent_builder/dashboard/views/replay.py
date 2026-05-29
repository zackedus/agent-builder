"""Tab 4 — Session replay (placeholder until F5.5)."""

from __future__ import annotations

from typing import Any

from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens


def build_replay_view(store: DashboardStore, tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    count = len(store.events)
    return ft.Container(
        expand=True,
        padding=16,
        bgcolor=tokens.surface,
        border_radius=8,
        content=ft.Column(
            [
                ft.Text("Replay", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(f"{count} events in log", color=tokens.on_surface),
                ft.Text("Timeline scrubber ships in F5.5.", size=12, italic=True),
            ],
            expand=True,
        ),
    )
