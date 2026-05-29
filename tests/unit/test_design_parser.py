"""Unit tests for design.json parsing (F4.2.3 / F4.2.5)."""

from __future__ import annotations

import pytest

from agent_builder.agents.design_parser import DesignParseError, parse_design
from tests.unit.fixtures.design_responses import (
    CHART_DESIGN_JSON,
    FORM_DESIGN_JSON,
    LIST_DESIGN_JSON,
    NAVIGATION_DESIGN_JSON,
)


@pytest.mark.parametrize(
    ("payload", "screen_id", "widget_types"),
    [
        (FORM_DESIGN_JSON, "expense_form", {"TextField", "Dropdown", "ElevatedButton"}),
        (LIST_DESIGN_JSON, "todo_list", {"AppBar", "ListView", "ElevatedButton"}),
        (NAVIGATION_DESIGN_JSON, "app_shell", {"NavigationRail", "Column"}),
        (CHART_DESIGN_JSON, "sales_dashboard", {"Text", "LineChart"}),
    ],
)
def test_parse_design_screen_patterns(
    payload: str,
    screen_id: str,
    widget_types: set[str],
) -> None:
    design = parse_design(payload)
    assert design.screen_id == screen_id
    assert {w.type for w in design.widgets} == widget_types


def test_parse_design_rejects_empty_widgets() -> None:
    with pytest.raises(DesignParseError, match="at least one widget"):
        parse_design('{"screen_id": "x", "title": "Empty", "widgets": []}')
