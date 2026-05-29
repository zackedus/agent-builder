"""Dashboard color tokens, agent palette, and theme helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

AGENT_COLORS: dict[str, dict[str, str]] = {
    "planner": {"bg": "#EEEDFE", "fg": "#3C3489"},
    "indexer": {"bg": "#F1EFE8", "fg": "#444441"},
    "designer": {"bg": "#FBEAF0", "fg": "#72243E"},
    "coder": {"bg": "#E6F1FB", "fg": "#0C447C"},
    "tester": {"bg": "#FAEEDA", "fg": "#633806"},
    "reviewer": {"bg": "#E1F5EE", "fg": "#085041"},
    "devops": {"bg": "#FAECE7", "fg": "#712B13"},
}

DEFAULT_AGENT_COLOR = {"bg": "#F3F4F6", "fg": "#374151"}

TAB_LABELS = ("Kanban", "Dependency", "Cost", "Replay")


@dataclass(frozen=True)
class DashboardThemeTokens:
    """Semantic colors for light/dark dashboard chrome."""

    surface: str
    surface_variant: str
    on_surface: str
    primary: str
    border: str
    feed_background: str


LIGHT_TOKENS = DashboardThemeTokens(
    surface="#FFFFFF",
    surface_variant="#F8FAFC",
    on_surface="#111827",
    primary="#2563EB",
    border="#E5E7EB",
    feed_background="#F9FAFB",
)

DARK_TOKENS = DashboardThemeTokens(
    surface="#1F2937",
    surface_variant="#111827",
    on_surface="#F9FAFB",
    primary="#60A5FA",
    border="#374151",
    feed_background="#0F172A",
)


def tokens_for_mode(*, dark: bool) -> DashboardThemeTokens:
    return DARK_TOKENS if dark else LIGHT_TOKENS


def agent_color(agent: str) -> dict[str, str]:
    return AGENT_COLORS.get(agent.lower(), DEFAULT_AGENT_COLOR)


def apply_page_theme(page: Any, *, dark: bool) -> DashboardThemeTokens:
    """Apply Flet theme mode and return active tokens."""
    import flet as ft

    page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT
    page.bgcolor = tokens_for_mode(dark=dark).surface_variant
    return tokens_for_mode(dark=dark)
