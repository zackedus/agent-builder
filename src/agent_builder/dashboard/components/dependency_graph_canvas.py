"""Flet canvas + node stack for the dependency graph."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent_builder.core.state import TaskNode, TaskStatus
from agent_builder.dashboard.graph.sugiyama_layout import GraphLayout, node_radius
from agent_builder.dashboard.theme import DashboardThemeTokens, agent_color


def build_dependency_graph_canvas(
    layout: GraphLayout,
    tasks_by_id: dict[str, TaskNode],
    tokens: DashboardThemeTokens,
    *,
    zoom: float,
    pan_x: float,
    pan_y: float,
    selected_task_id: str | None,
    on_node_click: Callable[[str], None] | None = None,
) -> Any:
    import flet as ft
    import flet.canvas as cv

    stroke = ft.Paint(style=ft.PaintingStyle.STROKE, stroke_width=2, color=tokens.border)
    critical_stroke = ft.Paint(
        style=ft.PaintingStyle.STROKE,
        stroke_width=3,
        color=tokens.primary,
    )

    shapes: list[Any] = []
    for edge in layout.edges:
        paint = critical_stroke if edge.on_critical_path else stroke
        shapes.append(cv.Line(edge.x1, edge.y1, edge.x2, edge.y2, paint=paint))

    canvas = cv.Canvas(
        shapes=shapes,
        width=layout.width,
        height=layout.height,
    )

    node_controls: list[Any] = []
    for layout_node in layout.nodes:
        task = tasks_by_id.get(layout_node.task_id)
        if task is None:
            continue
        node_controls.append(
            _build_node_widget(
                task,
                layout_node.x,
                layout_node.y,
                layout_node.width,
                layout_node.height,
                tokens,
                selected=task.id == selected_task_id,
                on_click=on_node_click,
            ),
        )

    graph_stack = ft.Stack(
        [canvas, ft.Stack(node_controls, width=layout.width, height=layout.height)],
        width=layout.width,
        height=layout.height,
    )

    scaled_width = layout.width * zoom
    scaled_height = layout.height * zoom

    return ft.Container(
        content=ft.Stack(
            [
                ft.Container(
                    content=graph_stack,
                    scale=zoom,
                    left=pan_x,
                    top=pan_y,
                ),
            ],
            width=scaled_width + abs(pan_x) + 80,
            height=scaled_height + abs(pan_y) + 80,
        ),
        expand=True,
    )


def _build_node_widget(
    task: TaskNode,
    x: float,
    y: float,
    width: float,
    height: float,
    tokens: DashboardThemeTokens,
    *,
    selected: bool,
    on_click: Callable[[str], None] | None,
) -> Any:
    import flet as ft

    colors = agent_color(task.assigned_agent)
    status = TaskStatus(task.status)
    border_width = 1 + min(task.retry_count, 3)
    if task.on_critical_path:
        border_width = max(border_width, 3)
    if selected:
        border_width = max(border_width, 3)

    border_color = tokens.primary if selected or task.on_critical_path else colors["fg"]
    if status in (
        TaskStatus.BLOCKED_RETRY_EXCEEDED,
        TaskStatus.BLOCKED_NEEDS_INPUT,
        TaskStatus.FAILED_UNRECOVERABLE,
    ):
        border_color = "#DC2626"

    radius = node_radius(task)
    tooltip = f"{task.id}\n{task.title}\n{task.assigned_agent} · {status.value}"

    def handle_click(_: Any) -> None:
        if on_click is not None:
            on_click(task.id)

    return ft.Container(
        left=x + (width - radius * 2) / 2,
        top=y + (height - radius * 2) / 2,
        width=radius * 2,
        height=radius * 2,
        tooltip=tooltip,
        on_click=handle_click,
        content=ft.Container(
            width=radius * 2,
            height=radius * 2,
            border_radius=radius,
            bgcolor=colors["bg"],
            border=ft.Border.all(border_width, border_color),
            alignment=ft.Alignment.CENTER,
            content=ft.Text(
                task.id,
                size=9,
                color=colors["fg"],
                weight=ft.FontWeight.W_600,
                text_align=ft.TextAlign.CENTER,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ),
    )
