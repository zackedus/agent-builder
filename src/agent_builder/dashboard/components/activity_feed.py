"""Live activity feed (bottom panel)."""

from __future__ import annotations

from typing import Any

from agent_builder.core.event_bus import Event, EventType
from agent_builder.dashboard.flet_ui import border_all
from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens


def format_event_line(event: Event) -> str:
    """Compact single-line summary for the feed."""
    ts = event.timestamp.strftime("%H:%M:%S")
    agent = event.payload.get("agent", "")
    extra = ""
    if event.type == EventType.STATE_CHANGED:
        extra = f"{event.payload.get('from')} → {event.payload.get('to')}"
    elif event.type == EventType.LLM_CALL:
        model = event.payload.get("model", "")
        extra = f"{agent or 'llm'} {model}".strip()
    elif event.type == EventType.TASK_FAILED:
        extra = str(event.payload.get("error", ""))[:80]
    else:
        extra = str(event.payload.get("task_id", "")) or str(event.payload.get("verdict", ""))
    label = event.type.value.replace("_", " ")
    detail = f" — {extra}" if extra else ""
    return f"[{ts}] {label}{detail}"


def build_activity_feed(store: DashboardStore, tokens: DashboardThemeTokens) -> Any:
    """Return a fixed-height feed container bound to *store*."""
    import flet as ft

    recent = store.events[-30:]
    lines = [format_event_line(event) for event in reversed(recent)]
    if not lines:
        lines = ["No events yet — start a build with agent-builder run …"]

    feed_list = ft.ListView(
        controls=[ft.Text(line, size=12, color=tokens.on_surface) for line in lines],
        spacing=4,
        expand=True,
        auto_scroll=True,
    )

    return ft.Container(
        height=140,
        bgcolor=tokens.feed_background,
        border=border_all(1, tokens.border),
        border_radius=8,
        padding=10,
        content=ft.Column(
            [
                ft.Text("Live activity", size=13, weight=ft.FontWeight.W_600),
                ft.Container(content=feed_list, expand=True),
            ],
            spacing=6,
        ),
    )
