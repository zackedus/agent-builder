"""Tab 2 — Interactive dependency graph (Sugiyama layout + Flet canvas)."""

from __future__ import annotations

from typing import Any

from agent_builder.dashboard.components.dependency_graph_canvas import build_dependency_graph_canvas
from agent_builder.dashboard.graph.filters import (
    STATUS_FILTER_LABELS,
    filter_graph_tasks,
    unique_agents,
)
from agent_builder.dashboard.graph.sugiyama_layout import compute_sugiyama_layout
from agent_builder.dashboard.state.kanban_tasks import resolve_kanban_tasks
from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens


def build_dependency_view(store: DashboardStore, tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    all_tasks = resolve_kanban_tasks(store.session_for_views(), store.plan)
    filtered = filter_graph_tasks(
        all_tasks,
        status_filter=store.graph_status_filter,
        agent_filter=store.graph_agent_filter,
        show_completed=store.graph_show_completed,
    )
    layout = compute_sugiyama_layout(filtered)
    tasks_by_id = {t.id: t for t in filtered}

    def select_node(task_id: str) -> None:
        current = store.selected_task_id
        store.select_task(None if task_id == current else task_id)

    status_options = [ft.dropdown.Option(key, text) for key, text in STATUS_FILTER_LABELS]
    agent_options = [ft.dropdown.Option("all", "Semua agent")]
    agent_options.extend(ft.dropdown.Option(a, a) for a in unique_agents(all_tasks))

    status_dropdown = ft.Dropdown(
        label="Status",
        width=180,
        value=store.graph_status_filter,
        options=status_options,
        on_select=lambda e: store.set_graph_filters(status=str(e.control.value)),
    )
    agent_dropdown = ft.Dropdown(
        label="Agent",
        width=160,
        value=store.graph_agent_filter,
        options=agent_options,
        on_select=lambda e: store.set_graph_filters(agent=str(e.control.value)),
    )
    show_completed = ft.Switch(
        label="Tampilkan selesai",
        value=store.graph_show_completed,
        on_change=lambda e: store.set_graph_filters(show_completed=bool(e.control.value)),
    )

    def zoom_in(_: Any) -> None:
        store.set_graph_zoom(store.graph_zoom + 0.15)

    def zoom_out(_: Any) -> None:
        store.set_graph_zoom(store.graph_zoom - 0.15)

    def reset_view(_: Any) -> None:
        store.reset_graph_view()

    toolbar = ft.Row(
        [
            status_dropdown,
            agent_dropdown,
            show_completed,
            ft.IconButton(ft.Icons.ZOOM_IN, tooltip="Zoom in", on_click=zoom_in),
            ft.IconButton(ft.Icons.ZOOM_OUT, tooltip="Zoom out", on_click=zoom_out),
            ft.TextButton("Reset view", on_click=reset_view),
            ft.Container(expand=True),
            ft.Text(f"{len(filtered)} task · zoom {store.graph_zoom:.0%}", size=12),
        ],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
    )

    if not filtered:
        return ft.Container(
            expand=True,
            padding=16,
            content=ft.Column(
                [
                    toolbar,
                    ft.Text(
                        "Tidak ada task untuk filter ini.",
                        size=14,
                        color=tokens.on_surface,
                        italic=True,
                    ),
                ],
                expand=True,
            ),
        )

    graph_body = build_dependency_graph_canvas(
        layout,
        tasks_by_id,
        tokens,
        zoom=store.graph_zoom,
        pan_x=store.graph_pan_x,
        pan_y=store.graph_pan_y,
        selected_task_id=store.selected_task_id,
        on_node_click=select_node,
    )

    pan_state: dict[str, float | None] = {"last_x": None, "last_y": None}
    pan_delta: dict[str, float] = {"dx": 0.0, "dy": 0.0}

    def on_pan_start(e: Any) -> None:
        pan_state["last_x"] = e.local_x
        pan_state["last_y"] = e.local_y
        pan_delta["dx"] = 0.0
        pan_delta["dy"] = 0.0

    def on_pan_update(e: Any) -> None:
        last_x = pan_state["last_x"]
        last_y = pan_state["last_y"]
        if last_x is None or last_y is None:
            return
        pan_delta["dx"] += e.local_x - last_x
        pan_delta["dy"] += e.local_y - last_y
        pan_state["last_x"] = e.local_x
        pan_state["last_y"] = e.local_y

    def on_pan_end(_: Any) -> None:
        if pan_delta["dx"] or pan_delta["dy"]:
            store.adjust_graph_pan(pan_delta["dx"], pan_delta["dy"])
        pan_state["last_x"] = None
        pan_state["last_y"] = None

    def on_scroll(e: Any) -> None:
        delta = getattr(e, "scroll_delta_y", 0) or 0
        if delta < 0:
            store.set_graph_zoom(store.graph_zoom + 0.1)
        elif delta > 0:
            store.set_graph_zoom(store.graph_zoom - 0.1)

    scrollable = ft.GestureDetector(
        content=ft.Container(
            content=graph_body,
            expand=True,
            bgcolor=tokens.surface_variant,
            border_radius=8,
            padding=8,
        ),
        on_pan_start=on_pan_start,
        on_pan_update=on_pan_update,
        on_pan_end=on_pan_end,
        on_scroll=on_scroll,
        drag_interval=8,
    )

    legend = ft.Row(
        [
            ft.Text("● warna = agent", size=11, color=tokens.on_surface),
            ft.Text("tebal = critical path / retry", size=11, color=tokens.on_surface),
            ft.Text("klik node = pilih task", size=11, color=tokens.on_surface),
        ],
        spacing=16,
    )

    return ft.Container(
        expand=True,
        padding=8,
        content=ft.Column(
            [
                toolbar,
                legend,
                scrollable,
            ],
            expand=True,
            spacing=8,
        ),
    )
