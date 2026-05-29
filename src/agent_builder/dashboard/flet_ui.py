"""Flet UI helpers compatible with Flet 0.24+ (TabBar/TabBarView API)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast


def border_all(width: float, color: str) -> Any:
    """Uniform border (Flet 0.85 uses ``ft.Border``, older docs use ``ft.border``)."""
    import flet as ft

    border_cls = getattr(ft, "Border", None)
    if border_cls is not None:
        return border_cls.all(width, color)
    legacy = getattr(ft, "border", None)
    if legacy is not None and hasattr(legacy, "all"):
        return cast(Any, legacy.all(width, color))
    raise RuntimeError("Unsupported Flet version: no Border API")


def configure_window(page: Any, *, width: int = 1200, height: int = 800) -> None:
    """Set initial window size when supported (desktop)."""
    window = getattr(page, "window", None)
    if window is not None:
        window.width = width
        window.height = height


def build_tabs_shell(
    labels: Sequence[str],
    *,
    selected_index: int,
    panel_builders: Sequence[Callable[[], Any]],
    on_change: Callable[[Any], None],
) -> tuple[Any, Any]:
    """Return ``(tabs, tab_bar_view)`` using Flet 0.24+ TabBar/TabBarView layout."""
    import flet as ft

    count = len(labels)
    panels = [builder() for builder in panel_builders]
    tab_bar = ft.TabBar(tabs=[ft.Tab(label=label) for label in labels])
    tab_bar_view = ft.TabBarView(expand=True, controls=panels)
    tabs = ft.Tabs(
        length=count,
        selected_index=selected_index,
        on_change=on_change,
        expand=True,
        content=ft.Column(
            expand=True,
            spacing=0,
            controls=[tab_bar, tab_bar_view],
        ),
    )
    return tabs, tab_bar_view


def launch_app(target: Callable[[Any], None]) -> None:
    """Start the dashboard Flet app (``run`` or legacy ``app``)."""
    import flet as ft

    run_fn = getattr(ft, "run", None)
    if callable(run_fn):
        run_fn(target)
        return
    app_fn = getattr(ft, "app", None)
    if callable(app_fn):
        app_fn(target=target)
        return
    raise RuntimeError("Unsupported Flet version: neither run() nor app() found")
