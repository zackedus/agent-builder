"""Sugiyama layered layout for dependency DAGs."""

from __future__ import annotations

from dataclasses import dataclass

from agent_builder.core.state import Complexity, TaskNode

NODE_WIDTH = 128.0
NODE_HEIGHT = 52.0
H_GAP = 200.0
V_GAP = 72.0
MARGIN = 40.0

_COMPLEXITY_RADIUS: dict[Complexity, float] = {
    "small": 18.0,
    "medium": 22.0,
    "large": 28.0,
}


@dataclass(frozen=True)
class LayoutNode:
    task_id: str
    x: float
    y: float
    layer: int
    width: float = NODE_WIDTH
    height: float = NODE_HEIGHT


@dataclass(frozen=True)
class LayoutEdge:
    source_id: str
    target_id: str
    x1: float
    y1: float
    x2: float
    y2: float
    on_critical_path: bool


@dataclass(frozen=True)
class GraphLayout:
    nodes: tuple[LayoutNode, ...]
    edges: tuple[LayoutEdge, ...]
    width: float
    height: float


def compute_sugiyama_layout(tasks: list[TaskNode]) -> GraphLayout:
    """Assign layered (x, y) positions for *tasks* and connecting edges."""
    if not tasks:
        return GraphLayout(nodes=(), edges=(), width=400.0, height=200.0)

    by_id = {t.id: t for t in tasks}
    layers = _assign_layers(by_id)
    max_layer = max(layers.values()) if layers else 0
    layer_buckets: dict[int, list[str]] = {i: [] for i in range(max_layer + 1)}
    for task_id, layer in sorted(layers.items(), key=lambda item: (item[1], item[0])):
        layer_buckets[layer].append(task_id)

    positioned: list[LayoutNode] = []
    max_rows = 1
    for layer_index, ids in layer_buckets.items():
        ids.sort()
        max_rows = max(max_rows, len(ids))
        for row_index, task_id in enumerate(ids):
            x = MARGIN + layer_index * (NODE_WIDTH + H_GAP)
            y = MARGIN + row_index * (NODE_HEIGHT + V_GAP)
            positioned.append(
                LayoutNode(task_id=task_id, x=x, y=y, layer=layer_index),
            )

    pos_by_id = {n.task_id: n for n in positioned}
    edges: list[LayoutEdge] = []
    for task in tasks:
        source = pos_by_id.get(task.id)
        if source is None:
            continue
        for dep_id in task.depends_on:
            target = pos_by_id.get(dep_id)
            if target is None:
                continue
            x1 = target.x + target.width
            y1 = target.y + target.height / 2
            x2 = source.x
            y2 = source.y + source.height / 2
            critical = task.on_critical_path and by_id[dep_id].on_critical_path
            edges.append(
                LayoutEdge(
                    source_id=dep_id,
                    target_id=task.id,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    on_critical_path=critical,
                ),
            )

    width = MARGIN * 2 + (max_layer + 1) * NODE_WIDTH + max_layer * H_GAP
    height = MARGIN * 2 + max_rows * NODE_HEIGHT + (max_rows - 1) * V_GAP
    return GraphLayout(
        nodes=tuple(positioned),
        edges=tuple(edges),
        width=max(width, 400.0),
        height=max(height, 200.0),
    )


def node_radius(task: TaskNode) -> float:
    return _COMPLEXITY_RADIUS.get(task.estimated_complexity, _COMPLEXITY_RADIUS["medium"])


def _assign_layers(by_id: dict[str, TaskNode]) -> dict[str, int]:
    layer: dict[str, int] = {}
    memo: dict[str, int] = {}

    def depth(task_id: str, visiting: set[str]) -> int:
        if task_id in memo:
            return memo[task_id]
        if task_id in visiting:
            return 0
        visiting.add(task_id)
        node = by_id.get(task_id)
        if node is None:
            result = 0
        elif not node.depends_on:
            result = 0
        else:
            deps = [d for d in node.depends_on if d in by_id]
            result = max((depth(dep, visiting) + 1 for dep in deps), default=0)
        visiting.remove(task_id)
        memo[task_id] = result
        layer[task_id] = result
        return result

    for task_id in by_id:
        depth(task_id, set())
    return layer
