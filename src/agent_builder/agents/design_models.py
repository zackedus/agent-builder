"""Pydantic models for UI design specs (``designs/{task_id}.json``)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FLET_WIDGET_TYPES = frozenset(
    {
        "Text",
        "TextField",
        "Dropdown",
        "Checkbox",
        "Switch",
        "Slider",
        "ElevatedButton",
        "OutlinedButton",
        "IconButton",
        "ListView",
        "Column",
        "Row",
        "Container",
        "Card",
        "DataTable",
        "NavigationBar",
        "NavigationRail",
        "AppBar",
        "Tabs",
        "Tab",
        "Chart",
        "LineChart",
        "BarChart",
        "PieChart",
    }
)

LayoutType = Literal["column", "row", "stack"]


class WidgetSpec(BaseModel):
    """One Flet widget in a screen."""

    model_config = ConfigDict(extra="allow")

    type: str
    id: str
    label: str | None = None


class NavigationSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    back_to: str | None = None
    next_on_success: str | None = None


class ScreenDesign(BaseModel):
    """Structured Flet screen specification for the Coder."""

    model_config = ConfigDict(extra="allow")

    screen_id: str
    title: str
    layout: LayoutType = "column"
    widgets: list[WidgetSpec] = Field(default_factory=list)
    navigation: NavigationSpec | None = None
    responsive_breakpoints: dict[str, str] | None = None
