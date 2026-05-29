from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.core.event_bus import EventType
from agent_builder.core.exceptions import StateNotFoundError, StateTransitionError
from agent_builder.core.orchestrator import (
    Orchestrator,
    OrchestratorEvent,
    TransitionContext,
    resolve_next_state,
    walk_happy_path,
)
from agent_builder.core.state import OrchestratorState, Plan, PlanTask, SessionState
from agent_builder.core.workspace import Workspace


@pytest.fixture
def orch(workspace: Workspace) -> Orchestrator:
    return Orchestrator(workspace)


@pytest.mark.asyncio
async def test_execute_planning_success(orch: Orchestrator) -> None:
    orch.start("Build calculator")
    plan_json = """
    {
      "project_name": "calc",
      "description": "CLI calc",
      "tasks": [{
        "id": "T1.1", "title": "Script", "type": "logic",
        "acceptance_criteria": ["runs"]
      }],
      "estimated_complexity": "small",
      "risks": []
    }
    """
    from agent_builder.agents.base import AgentResult
    from agent_builder.agents.plan_parser import parse_plan

    plan = parse_plan(plan_json)
    mock_result = AgentResult(success=True, data={"plan": plan})

    with patch(
        "agent_builder.agents.planner.PlannerAgent.run",
        AsyncMock(return_value=mock_result),
    ):
        result = await orch.execute_planning()

    assert result is not None
    assert orch.session is not None
    assert orch.session.current_state == OrchestratorState.PLAN_APPROVAL
    assert orch.workspace.load_plan() is not None


@pytest.mark.asyncio
async def test_execute_testing_pass(orch: Orchestrator) -> None:
    orch.start("app")
    plan = Plan(
        project_name="x",
        description="d",
        tasks=[
            PlanTask(
                id="T1.1",
                title="Mod",
                type="logic",
                files_affected=["m.py"],
                acceptance_criteria=["imports"],
            )
        ],
    )
    orch.workspace.project_dir.mkdir(parents=True, exist_ok=True)
    (orch.workspace.project_dir / "m.py").write_text("x = 1\n", encoding="utf-8")
    orch.dispatch(OrchestratorEvent.PLAN_VALID, TransitionContext(plan=plan))
    orch.dispatch(OrchestratorEvent.AUTO_APPROVE, TransitionContext(plan=plan, task_id="T1.1"))
    orch.dispatch(OrchestratorEvent.NEXT_TASK, TransitionContext(task_id="T1.1"))
    orch.dispatch(OrchestratorEvent.INDEXING_DONE)
    orch.dispatch(OrchestratorEvent.CODE_WRITTEN)

    from agent_builder.agents.base import AgentResult
    from agent_builder.agents.test_models import TesterReport

    mock_result = AgentResult(
        success=True,
        data={
            "test_result": TesterReport(
                task_id="T1.1",
                status="passed",
                static_checks={"ruff": "passed", "mypy": "passed"},
                smoke="passed",
            ),
        },
    )
    with patch(
        "agent_builder.agents.tester.TesterAgent.run",
        AsyncMock(return_value=mock_result),
    ):
        ok = await orch.execute_testing()

    assert ok is True
    assert orch.session is not None
    assert orch.session.current_state == OrchestratorState.REVIEWING


@pytest.mark.asyncio
async def test_execute_coding_writes_project_files(orch: Orchestrator) -> None:
    orch.start("calc app")
    plan = Plan(
        project_name="calc",
        description="CLI calc",
        tasks=[
            PlanTask(
                id="T1.1",
                title="Script",
                type="logic",
                files_affected=["calc.py"],
                acceptance_criteria=["runs"],
            )
        ],
    )
    orch.dispatch(OrchestratorEvent.PLAN_VALID, TransitionContext(plan=plan))
    orch.dispatch(OrchestratorEvent.AUTO_APPROVE, TransitionContext(plan=plan, task_id="T1.1"))
    orch.dispatch(OrchestratorEvent.NEXT_TASK, TransitionContext(task_id="T1.1"))
    orch.dispatch(OrchestratorEvent.INDEXING_DONE)

    from agent_builder.agents.base import AgentResult

    mock_result = AgentResult(success=True, data={"files": ["calc.py"]})
    with patch(
        "agent_builder.agents.coder.CoderAgent.run",
        AsyncMock(return_value=mock_result),
    ):
        ok = await orch.execute_coding()

    assert ok is True
    assert orch.session is not None
    assert orch.session.current_state == OrchestratorState.TESTING


@pytest.mark.asyncio
async def test_advance_task_loop_picks_next_task(orch: Orchestrator) -> None:
    plan = Plan(
        project_name="x",
        description="d",
        tasks=[
            PlanTask(id="T1", title="A", type="scaffold"),
            PlanTask(id="T2", title="B", type="logic", depends_on=["T1"]),
        ],
    )
    orch.start("multi")
    orch.dispatch(OrchestratorEvent.PLAN_VALID, TransitionContext(plan=plan))
    orch.dispatch(OrchestratorEvent.AUTO_APPROVE, TransitionContext(plan=plan, task_id="T1"))
    orch.session.completed_tasks = ["T1"]
    orch.session.current_state = OrchestratorState.TASK_LOOP

    orch.advance_task_loop()
    assert orch.session is not None
    assert orch.session.current_task == "T2"
    assert orch.session.current_state == OrchestratorState.INDEXING


@pytest.mark.asyncio
async def test_execute_planning_invalid_stays_planning(orch: Orchestrator) -> None:
    orch.start("bad plan")
    from agent_builder.agents.base import AgentResult

    with patch(
        "agent_builder.agents.planner.PlannerAgent.run",
        AsyncMock(return_value=AgentResult(success=False, output="parse error")),
    ):
        result = await orch.execute_planning()

    assert result is None
    assert orch.session is not None
    assert orch.session.current_state == OrchestratorState.PLANNING


def test_start_transitions_idle_to_planning(orch: Orchestrator) -> None:
    session = orch.start("Build a todo app")
    assert session.current_state == OrchestratorState.PLANNING
    assert session.user_prompt == "Build a todo app"
    assert orch.workspace.state_path.is_file()


def test_resume_loads_persisted_session(orch: Orchestrator) -> None:
    session = orch.start("Resume me")
    session_id = session.session_id

    other = Orchestrator(orch.workspace)
    resumed = other.resume()
    assert resumed is not None
    assert resumed.session_id == session_id
    assert resumed.current_state == OrchestratorState.PLANNING


def test_invalid_transition_raises(orch: Orchestrator) -> None:
    orch.start("test")
    with pytest.raises(StateTransitionError):
        orch.dispatch(OrchestratorEvent.BUILT)


def test_dispatch_without_session_raises(workspace: Workspace) -> None:
    orch = Orchestrator(workspace)
    with pytest.raises(StateNotFoundError):
        orch.dispatch(OrchestratorEvent.PLAN_VALID)


def test_tests_fail_retries_then_failed(orch: Orchestrator) -> None:
    orch.start("app")
    orch.dispatch(OrchestratorEvent.PLAN_VALID)
    orch.dispatch(OrchestratorEvent.AUTO_APPROVE, TransitionContext(task_id="T1"))
    orch.dispatch(OrchestratorEvent.NEXT_TASK, TransitionContext(task_id="T1"))
    orch.dispatch(OrchestratorEvent.INDEXING_DONE)
    orch.dispatch(OrchestratorEvent.CODE_WRITTEN)

    for _ in range(3):
        orch.dispatch(OrchestratorEvent.TESTS_FAIL)
        assert orch.session is not None
        assert orch.session.current_state == OrchestratorState.CODING
        orch.dispatch(OrchestratorEvent.CODE_WRITTEN)

    orch.dispatch(OrchestratorEvent.TESTS_FAIL)
    assert orch.session is not None
    assert orch.session.current_state == OrchestratorState.FAILED

    with pytest.raises(StateTransitionError):
        orch.dispatch(OrchestratorEvent.CODE_WRITTEN)


def test_indexing_done_branches_to_designing(orch: Orchestrator) -> None:
    orch.start("ui app")
    orch.dispatch(OrchestratorEvent.PLAN_VALID)
    orch.dispatch(OrchestratorEvent.AUTO_APPROVE, TransitionContext(task_id="T1"))
    orch.dispatch(OrchestratorEvent.NEXT_TASK, TransitionContext(task_id="T1"))
    orch.dispatch(OrchestratorEvent.INDEXING_DONE, TransitionContext(requires_design=True))
    assert orch.session is not None
    assert orch.session.current_state == OrchestratorState.DESIGNING


def test_approved_marks_task_completed(orch: Orchestrator) -> None:
    orch.start("app")
    orch.dispatch(OrchestratorEvent.PLAN_VALID)
    orch.dispatch(OrchestratorEvent.AUTO_APPROVE, TransitionContext(task_id="T1"))
    orch.dispatch(OrchestratorEvent.NEXT_TASK, TransitionContext(task_id="T1"))
    orch.dispatch(OrchestratorEvent.INDEXING_DONE)
    orch.dispatch(OrchestratorEvent.CODE_WRITTEN)
    orch.dispatch(OrchestratorEvent.TESTS_PASS)
    orch.dispatch(OrchestratorEvent.APPROVED)
    assert orch.session is not None
    assert "T1" in orch.session.completed_tasks


def test_plan_valid_saves_plan(orch: Orchestrator) -> None:
    orch.start("app")
    plan = Plan(
        project_name="demo",
        description="Demo",
        tasks=[PlanTask(id="T1", title="Setup", type="scaffold")],
    )
    orch.dispatch(OrchestratorEvent.PLAN_VALID, TransitionContext(plan=plan))
    loaded = orch.workspace.load_plan()
    assert loaded is not None
    assert loaded.project_name == "demo"


def test_happy_path_idle_to_done(orch: Orchestrator) -> None:
    orch.start("full path")
    walk_happy_path(orch)
    assert orch.is_done()
    assert orch.session is not None
    assert orch.session.current_state == OrchestratorState.DONE


def test_happy_path_with_design_branch(orch: Orchestrator) -> None:
    orch.start("ui path")
    walk_happy_path(orch, requires_design=True)
    assert orch.is_done()


def test_resume_after_crash_continues_from_persisted_state(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "ws")
    first = Orchestrator(workspace)
    first.start("crash test")
    first.dispatch(OrchestratorEvent.PLAN_VALID)
    first.dispatch(OrchestratorEvent.AUTO_APPROVE, TransitionContext(task_id="T1"))

    second = Orchestrator(workspace)
    resumed = second.resume()
    assert resumed is not None
    assert resumed.current_state == OrchestratorState.TASK_LOOP
    second.dispatch(OrchestratorEvent.ALL_DONE)
    second.dispatch(OrchestratorEvent.INTEGRATION_PASS)
    second.dispatch(OrchestratorEvent.BUILT)
    assert second.is_done()


def test_state_changed_events_persisted(orch: Orchestrator) -> None:
    orch.start("events")
    orch.dispatch(OrchestratorEvent.PLAN_VALID)
    events = orch.workspace.events_store().load_all()
    types = [e.type for e in events]
    assert EventType.STATE_CHANGED in types


def test_resolve_next_state_tests_fail_branch() -> None:
    session = SessionState(current_task="T9")
    session.retry_count["T9"] = 2
    nxt = resolve_next_state(
        OrchestratorState.TESTING,
        OrchestratorEvent.TESTS_FAIL,
        session,
        TransitionContext(),
    )
    assert nxt == OrchestratorState.CODING

    session.retry_count["T9"] = 3
    failed = resolve_next_state(
        OrchestratorState.TESTING,
        OrchestratorEvent.TESTS_FAIL,
        session,
        TransitionContext(),
    )
    assert failed == OrchestratorState.FAILED


def test_terminal_session_rejects_dispatch(orch: Orchestrator) -> None:
    orch.start("done")
    walk_happy_path(orch)
    with pytest.raises(StateTransitionError):
        orch.dispatch(OrchestratorEvent.PLAN_VALID)


def test_integration_full_cycle_via_events_log(workspace: Workspace) -> None:
    orch = Orchestrator(workspace)
    orch.start("integration e2e")
    walk_happy_path(orch)

    store = workspace.events_store()
    events = store.load_all()
    state_events = [e for e in events if e.type == EventType.STATE_CHANGED]
    assert len(state_events) >= 10
    assert state_events[-1].payload["to"] == OrchestratorState.DONE.value

    reloaded = workspace.load_session()
    assert reloaded is not None
    assert reloaded.current_state == OrchestratorState.DONE
