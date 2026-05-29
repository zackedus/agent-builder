"""Plan task ordering and dependency-aware selection."""

from __future__ import annotations

from agent_builder.core.state import Plan, PlanTask


def order_plan_tasks(plan: Plan) -> list[PlanTask]:
    """Return tasks in dependency order (dependencies first)."""
    by_id = {t.id: t for t in plan.tasks}
    ordered: list[PlanTask] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in seen:
            return
        if task_id in visiting:
            return
        visiting.add(task_id)
        node = by_id.get(task_id)
        if node is None:
            visiting.remove(task_id)
            return
        for dep in node.depends_on:
            visit(dep)
        visiting.remove(task_id)
        seen.add(task_id)
        ordered.append(node)

    for task in plan.tasks:
        visit(task.id)
    return ordered


def next_executable_task(plan: Plan, completed: list[str]) -> PlanTask | None:
    """Return the next task whose dependencies are satisfied."""
    done = set(completed)
    for task in order_plan_tasks(plan):
        if task.id in done:
            continue
        if all(dep in done for dep in task.depends_on):
            return task
    return None
