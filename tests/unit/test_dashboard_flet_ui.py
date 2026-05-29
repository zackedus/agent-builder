"""Unit tests for Flet UI helpers (no GUI launch)."""

from __future__ import annotations

import pytest

pytest.importorskip("flet")

from agent_builder.dashboard.flet_ui import border_all, build_tabs_shell  # noqa: E402


def test_border_all_returns_border() -> None:
    border = border_all(1, "#E5E7EB")
    assert border is not None


def test_build_tabs_shell_structure() -> None:
    import flet as ft

    labels = ("A", "B")

    def on_change(_: object) -> None:
        pass

    tabs, tab_view = build_tabs_shell(
        labels,
        selected_index=0,
        panel_builders=[lambda: ft.Text("one"), lambda: ft.Text("two")],
        on_change=on_change,
    )
    assert tabs.length == 2
    assert len(tab_view.controls) == 2
    assert tabs.selected_index == 0
