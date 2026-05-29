"""Flet dashboard entry point — 4 tabs, metrics bar, activity feed."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent_builder.dashboard.components.activity_feed import build_activity_feed
from agent_builder.dashboard.flet_ui import build_tabs_shell, configure_window, launch_app
from agent_builder.dashboard.state.store import open_store
from agent_builder.dashboard.theme import (
    TAB_LABELS,
    DashboardThemeTokens,
    apply_page_theme,
    tokens_for_mode,
)
from agent_builder.dashboard.views import (
    build_cost_view,
    build_dependency_view,
    build_kanban_view,
    build_replay_view,
)


def run_dashboard(workspace_dir: Path | None = None, *, poll_interval_s: float = 2.0) -> None:
    """Launch the Flet dashboard for *workspace_dir* (or settings default)."""
    try:
        import flet as ft  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Dashboard requires Flet. Install with: pip install -e '.[dashboard]'"
        ) from exc

    store = open_store(workspace_dir)

    def main(page: Any) -> None:
        import flet as ft

        page.title = "Agent Team Builder"
        page.padding = 16
        configure_window(page, width=1200, height=800)

        tokens = apply_page_theme(page, dark=store.dark_mode)
        metrics_row = ft.Row(spacing=16)
        feed_host = ft.Container()

        def _tokens() -> DashboardThemeTokens:
            return tokens_for_mode(dark=store.dark_mode)

        view_builders: list[Callable[[], Any]] = [
            lambda: build_kanban_view(store, _tokens()),
            lambda: build_dependency_view(store, _tokens()),
            lambda: build_cost_view(store, _tokens()),
            lambda: build_replay_view(store, _tokens()),
        ]

        def on_tab_change(event: Any) -> None:
            store.set_active_tab(int(event.control.selected_index))

        tabs, tab_bar_view = build_tabs_shell(
            TAB_LABELS,
            selected_index=store.active_tab,
            panel_builders=view_builders,
            on_change=on_tab_change,
        )

        def render() -> None:
            nonlocal tokens
            tokens = apply_page_theme(page, dark=store.dark_mode)
            metrics = store.metrics()
            metrics_row.controls = [
                ft.Text(f"Progress {metrics.progress_label}", size=13),
                ft.Text(f"LLM {metrics.llm_calls}", size=13),
                ft.Text(f"${metrics.cost_usd:.4f}", size=13),
                ft.Text(f"Retries {metrics.retry_count}", size=13),
                ft.Text(f"State {metrics.orchestrator_state}", size=13, weight=ft.FontWeight.W_600),
            ]
            tab_bar_view.controls = [builder() for builder in view_builders]
            feed_host.content = build_activity_feed(store, tokens)
            tabs.selected_index = store.active_tab
            page.update()

        session_label = ft.Text("No active session", size=14, weight=ft.FontWeight.W_600)

        def refresh_header() -> None:
            if store.session:
                prompt = store.session.user_prompt[:48] or "—"
                session_label.value = f"Session {store.session.session_id[:8]}… — {prompt}"
            else:
                session_label.value = "No active session — agent-builder run …"
            session_label.update()

        def on_store_change() -> None:
            refresh_header()
            render()

        store.subscribe(on_store_change)

        def toggle_theme(_: Any) -> None:
            store.toggle_dark_mode()

        header = ft.Row(
            [
                ft.Text("Agent Team Builder", size=20, weight=ft.FontWeight.BOLD),
                session_label,
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.DARK_MODE if not store.dark_mode else ft.Icons.LIGHT_MODE,
                    tooltip="Toggle dark mode",
                    on_click=toggle_theme,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        layout = ft.Column(
            [
                header,
                tabs,
                metrics_row,
                feed_host,
            ],
            expand=True,
            spacing=12,
        )
        page.add(layout)
        on_store_change()

        async def poll_workspace() -> None:
            while True:
                await asyncio.sleep(poll_interval_s)
                store.refresh()

        page.run_task(poll_workspace)

    launch_app(main)


def main() -> None:
    """Console script entry."""
    run_dashboard()


if __name__ == "__main__":
    main()
