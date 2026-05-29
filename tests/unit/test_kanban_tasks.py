"""Unit tests for Kanban task resolution."""

from __future__ import annotations

from agent_builder.core.state import (
    OrchestratorState,
    Plan,
    PlanTask,
    SessionState,
    TaskStatus,
)
from agent_builder.dashboard.state.kanban_tasks import agent_for_plan_task, resolve_kanban_tasks


def test_resolve_kanban_tasks_done_and_running() -> None:
    plan = Plan(
        project_name="demo",
        description="x",
        tasks=[
            PlanTask(id="T1", title="Scaffold", type="scaffold"),
            PlanTask(id="T2", title="UI", type="ui", depends_on=["T1"]),
        ],
    )
    session = SessionState(
        completed_tasks=["T1"],
        current_task="T2",
        current_state=OrchestratorState.CODING,
    )
    tasks = resolve_kanban_tasks(session, plan)
    by_id = {t.id: t for t in tasks}
    assert TaskStatus(by_id["T1"].status) == TaskStatus.DONE
    assert TaskStatus(by_id["T2"].status) == TaskStatus.RUNNING
    assert agent_for_plan_task(plan.tasks[1]) == "designer"


def test_resolve_kanban_tasks_blocked_by_dependency() -> None:
    plan = Plan(
        project_name="demo",
        description="x",
        tasks=[
            PlanTask(id="T1", title="A", type="logic"),
            PlanTask(id="T2", title="B", type="logic", depends_on=["T1"]),
        ],
    )
    session = SessionState(current_task="T2", current_state=OrchestratorState.IDLE)
    tasks = resolve_kanban_tasks(session, plan)
    by_id = {t.id: t for t in tasks}
    assert TaskStatus(by_id["T2"].status) == TaskStatus.BLOCKED_BY_DEPENDENCY
    assert by_id["T2"].blocker_reason is not None
    assert "T1" in by_id["T2"].blocker_reason


def test_resolve_kanban_tasks_failed() -> None:
    plan = Plan(
        project_name="demo",
        description="x",
        tasks=[PlanTask(id="T1", title="A", type="logic")],
    )
    session = SessionState(failed_tasks=["T1"], retry_count={"T1": 2})
    tasks = resolve_kanban_tasks(session, plan)
    assert len(tasks) == 1
    assert TaskStatus(tasks[0].status) == TaskStatus.FAILED_UNRECOVERABLE
