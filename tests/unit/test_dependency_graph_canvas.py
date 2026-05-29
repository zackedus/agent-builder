"""Smoke tests for dependency graph canvas builder."""

from __future__ import annotations

import pytest

pytest.importorskip("flet")

from agent_builder.core.state import TaskNode  # noqa: E402
from agent_builder.dashboard.components.dependency_graph_canvas import (  # noqa: E402
    build_dependency_graph_canvas,
)
from agent_builder.dashboard.graph.sugiyama_layout import compute_sugiyama_layout  # noqa: E402
from agent_builder.dashboard.theme import tokens_for_mode  # noqa: E402


def test_build_dependency_graph_canvas_returns_container() -> None:
    tasks = [
        TaskNode(id="T1", title="A", assigned_agent="coder"),
        TaskNode(id="T2", title="B", assigned_agent="coder", depends_on=["T1"]),
    ]
    layout = compute_sugiyama_layout(tasks)
    widget = build_dependency_graph_canvas(
        layout,
        {t.id: t for t in tasks},
        tokens_for_mode(dark=False),
        zoom=1.0,
        pan_x=0.0,
        pan_y=0.0,
        selected_task_id="T1",
    )
    assert widget is not None
