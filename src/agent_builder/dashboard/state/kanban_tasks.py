"""Build Kanban task nodes from plan + session state."""

from __future__ import annotations

from agent_builder.core.state import (
    OrchestratorState,
    Plan,
    PlanTask,
    SessionState,
    TaskNode,
    TaskStatus,
    apply_critical_path_flags,
)

_TASK_TYPE_AGENT: dict[str, str] = {
    "ui": "designer",
    "logic": "coder",
    "scaffold": "coder",
    "default": "coder",
}

_RUNNING_STATES = frozenset(
    {
        OrchestratorState.INDEXING,
        OrchestratorState.DESIGNING,
        OrchestratorState.CODING,
        OrchestratorState.TESTING,
        OrchestratorState.REVIEWING,
    }
)

_BLOCKED_STATES = frozenset({OrchestratorState.FAILED})


def agent_for_plan_task(task: PlanTask) -> str:
    return _TASK_TYPE_AGENT.get(task.type, _TASK_TYPE_AGENT["default"])


def resolve_kanban_tasks(
    session: SessionState | None,
    plan: Plan | None,
) -> list[TaskNode]:
    """Synthesize ``TaskNode`` list for the dashboard from plan and session."""
    if plan is None or not plan.tasks:
        if session and session.tasks:
            return list(session.tasks)
        return []

    if session and session.tasks:
        nodes = list(session.tasks)
    else:
        nodes = [
            TaskNode(
                id=task.id,
                title=task.title,
                assigned_agent=agent_for_plan_task(task),
                depends_on=list(task.depends_on),
                estimated_complexity=plan.estimated_complexity,
            )
            for task in plan.tasks
        ]

    completed = set(session.completed_tasks) if session else set()
    failed = set(session.failed_tasks) if session else set()
    current = session.current_task if session else None
    orch_state = (
        OrchestratorState(session.current_state)
        if session and session.current_state
        else OrchestratorState.IDLE
    )

    updated: list[TaskNode] = []
    for node in nodes:
        status, reason = _derive_status(
            node,
            completed=completed,
            failed=failed,
            current_task=current,
            orchestrator_state=orch_state,
            retry_count=session.get_task_retry_count(node.id) if session else 0,
        )
        updated.append(
            node.model_copy(
                update={
                    "status": status,
                    "blocker_reason": reason,
                    "retry_count": session.get_task_retry_count(node.id) if session else 0,
                },
            ),
        )

    return apply_critical_path_flags(updated)


def _derive_status(
    node: TaskNode,
    *,
    completed: set[str],
    failed: set[str],
    current_task: str | None,
    orchestrator_state: OrchestratorState,
    retry_count: int,
) -> tuple[TaskStatus, str | None]:
    if node.id in completed:
        return TaskStatus.DONE, None
    if node.id in failed:
        return TaskStatus.FAILED_UNRECOVERABLE, "Task failed"

    if node.id == current_task:
        if orchestrator_state in _RUNNING_STATES:
            return TaskStatus.RUNNING, None
        if orchestrator_state in _BLOCKED_STATES or retry_count > 0:
            return TaskStatus.BLOCKED_RETRY_EXCEEDED, f"Retries: {retry_count}"
        if orchestrator_state == OrchestratorState.HUMAN_REVIEW:
            return TaskStatus.BLOCKED_NEEDS_INPUT, "Awaiting plan approval"

    if not all(dep in completed for dep in node.depends_on):
        waiting = ", ".join(dep for dep in node.depends_on if dep not in completed)
        return TaskStatus.BLOCKED_BY_DEPENDENCY, f"Waiting for {waiting}" if waiting else None

    return TaskStatus.PENDING, None
