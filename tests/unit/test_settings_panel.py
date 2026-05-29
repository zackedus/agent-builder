"""Unit tests for dashboard settings / run launcher."""

from __future__ import annotations

from agent_builder.dashboard.components.settings_panel import launch_build_in_terminal


def test_launch_build_rejects_empty_prompt() -> None:
    assert "kosong" in launch_build_in_terminal("   ").lower()
