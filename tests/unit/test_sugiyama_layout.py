"""Unit tests for Sugiyama graph layout."""

from __future__ import annotations

from agent_builder.core.state import TaskNode
from agent_builder.dashboard.graph.sugiyama_layout import compute_sugiyama_layout, node_radius


def test_compute_sugiyama_layout_layers() -> None:
    tasks = [
        TaskNode(id="T1", title="Root", assigned_agent="coder", depends_on=[]),
        TaskNode(
            id="T2",
            title="Child",
            assigned_agent="coder",
            depends_on=["T1"],
            on_critical_path=True,
        ),
    ]
    layout = compute_sugiyama_layout(tasks)
    assert len(layout.nodes) == 2
    assert len(layout.edges) == 1
    by_id = {n.task_id: n for n in layout.nodes}
    assert by_id["T2"].x > by_id["T1"].x
    assert layout.edges[0].source_id == "T1"
    assert layout.edges[0].target_id == "T2"


def test_compute_sugiyama_layout_empty() -> None:
    layout = compute_sugiyama_layout([])
    assert layout.nodes == ()
    assert layout.edges == ()


def test_node_radius_by_complexity() -> None:
    small = TaskNode(
        id="a",
        title="a",
        assigned_agent="coder",
        estimated_complexity="small",
    )
    large = TaskNode(
        id="b",
        title="b",
        assigned_agent="coder",
        estimated_complexity="large",
    )
    assert node_radius(large) > node_radius(small)
