"""Dashboard tab views."""

from agent_builder.dashboard.views.control import build_control_view
from agent_builder.dashboard.views.cost_breakdown import build_cost_view
from agent_builder.dashboard.views.dependency_graph import build_dependency_view
from agent_builder.dashboard.views.kanban import build_kanban_view
from agent_builder.dashboard.views.replay import build_replay_view

__all__ = [
    "build_control_view",
    "build_cost_view",
    "build_dependency_view",
    "build_kanban_view",
    "build_replay_view",
]
