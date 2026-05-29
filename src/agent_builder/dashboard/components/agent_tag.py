"""Colored agent name chip."""

from __future__ import annotations

from typing import Any

from agent_builder.dashboard.theme import agent_color


def build_agent_tag(agent: str) -> Any:
    import flet as ft

    colors = agent_color(agent)
    return ft.Container(
        content=ft.Text(agent, size=11, color=colors["fg"], weight=ft.FontWeight.W_500),
        bgcolor=colors["bg"],
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        border_radius=12,
    )
