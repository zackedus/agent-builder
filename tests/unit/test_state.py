import json

from agent_builder.core.state import (
    OrchestratorState,
    SessionState,
    TaskNode,
    TaskStatus,
    apply_critical_path_flags,
    compute_critical_path,
    plan_from_json,
    session_state_from_json,
    session_state_to_json,
)


def test_session_state_roundtrip_json() -> None:
    state = SessionState(
        user_prompt="Build a todo app",
        current_state=OrchestratorState.PLANNING,
        current_task="T1.1",
        retry_count={"T1.1": 1},
        completed_tasks=["T0.1"],
    )
    restored = session_state_from_json(session_state_to_json(state))
    assert restored.user_prompt == state.user_prompt
    assert restored.current_state == OrchestratorState.PLANNING
    assert restored.current_task == "T1.1"
    assert restored.retry_count == {"T1.1": 1}
    assert restored.completed_tasks == ["T0.1"]
    assert restored.session_id == state.session_id


def test_session_state_matches_architecture_schema() -> None:
    raw = json.dumps(
        {
            "session_id": "abc-123",
            "started_at": "2026-05-29T10:00:00+00:00",
            "current_state": "CODING",
            "current_task": "T2.3",
            "user_prompt": "Build expense tracker",
            "retry_count": {"T2.3": 1},
            "completed_tasks": ["T1.1", "T1.2"],
            "failed_tasks": [],
            "metrics": {
                "total_llm_calls": 47,
                "total_cost_usd": 3.21,
                "elapsed_seconds": 1820,
            },
        }
    )
    state = session_state_from_json(raw)
    assert state.current_state == OrchestratorState.CODING
    assert state.metrics.total_llm_calls == 47


def test_session_increment_retry() -> None:
    state = SessionState()
    assert state.increment_task_retry("T1.1") == 1
    assert state.increment_task_retry("T1.1") == 2
    assert state.get_task_retry_count("T1.1") == 2


def test_session_terminal_states() -> None:
    idle = SessionState(current_state=OrchestratorState.IDLE)
    done = SessionState(current_state=OrchestratorState.DONE)
    assert idle.is_terminal() is False
    assert done.is_terminal() is True


def test_plan_from_json() -> None:
    raw = json.dumps(
        {
            "project_name": "expense_tracker",
            "description": "Expense tracker app",
            "tech_stack": {"gui": "flet", "storage": "sqlite"},
            "tasks": [
                {
                    "id": "T1.1",
                    "title": "Scaffold project",
                    "type": "scaffold",
                    "depends_on": [],
                    "files_affected": ["pyproject.toml"],
                    "acceptance_criteria": ["pip install works"],
                }
            ],
            "estimated_complexity": "medium",
            "risks": [],
        }
    )
    plan = plan_from_json(raw)
    assert plan.project_name == "expense_tracker"
    assert len(plan.tasks) == 1
    assert plan.tasks[0].id == "T1.1"


def test_compute_critical_path() -> None:
    tasks = [
        TaskNode(
            id="T1",
            title="Root",
            assigned_agent="coder",
            depends_on=[],
            estimated_complexity="small",
        ),
        TaskNode(
            id="T2",
            title="Middle",
            assigned_agent="coder",
            depends_on=["T1"],
            estimated_complexity="medium",
        ),
        TaskNode(
            id="T3",
            title="Leaf",
            assigned_agent="coder",
            depends_on=["T2"],
            estimated_complexity="large",
        ),
    ]
    critical = compute_critical_path(tasks)
    assert critical == {"T1", "T2", "T3"}


def test_apply_critical_path_flags() -> None:
    tasks = [
        TaskNode(id="A", title="A", assigned_agent="coder"),
        TaskNode(id="B", title="B", assigned_agent="coder", depends_on=["A"]),
    ]
    flagged = apply_critical_path_flags(tasks)
    assert flagged[0].on_critical_path is True
    assert flagged[1].on_critical_path is True


def test_task_status_enum_values() -> None:
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
