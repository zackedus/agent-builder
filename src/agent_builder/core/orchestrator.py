"""FSM orchestrator for the agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agent_builder.agents.base import AgentContext
from agent_builder.agents.coder import CoderAgent
from agent_builder.agents.planner import PlannerAgent
from agent_builder.agents.review_models import ReviewResult
from agent_builder.agents.review_parser import format_review_feedback
from agent_builder.agents.reviewer import ReviewerAgent
from agent_builder.agents.task_selection import next_executable_task
from agent_builder.agents.test_models import TesterReport
from agent_builder.agents.tester import TesterAgent
from agent_builder.config import Settings, get_settings
from agent_builder.core.event_bus import Event, EventBus, EventType
from agent_builder.core.exceptions import StateNotFoundError, StateTransitionError
from agent_builder.core.state import OrchestratorState, Plan, PlanTask, SessionState
from agent_builder.core.workspace import Workspace

if TYPE_CHECKING:
    from agent_builder.llm.router import LLMRouter


class OrchestratorEvent:
    """Transition trigger events (ARCHITECTURE.md §5.2)."""

    PROMPT_RECEIVED = "prompt_received"
    PLAN_VALID = "plan_valid"
    PLAN_INVALID = "plan_invalid"
    AUTO_APPROVE = "auto_approve"
    USER_OK = "user_ok"
    NEXT_TASK = "next_task"
    INDEXING_DONE = "indexing_done"
    DESIGN_READY = "design_ready"
    CODE_WRITTEN = "code_written"
    TESTS_PASS = "tests_pass"
    TESTS_FAIL = "tests_fail"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    ALL_DONE = "all_done"
    INTEGRATION_PASS = "integration_pass"
    BUILT = "built"


@dataclass
class TransitionContext:
    """Extra data needed to resolve branching transitions."""

    requires_design: bool = False
    task_id: str | None = None
    plan: Plan | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StateTransition:
    from_state: OrchestratorState
    event: str
    to_state: OrchestratorState


def _transition(
    from_state: OrchestratorState,
    event: str,
    to_state: OrchestratorState,
) -> StateTransition:
    return StateTransition(from_state, event, to_state)


# Static transitions without branching (branching handled in ``resolve_next_state``).
_S = OrchestratorState
_E = OrchestratorEvent
_TRANSITIONS: tuple[StateTransition, ...] = (
    _transition(_S.IDLE, _E.PROMPT_RECEIVED, _S.PLANNING),
    _transition(_S.PLANNING, _E.PLAN_VALID, _S.PLAN_APPROVAL),
    _transition(_S.PLANNING, _E.PLAN_INVALID, _S.PLANNING),
    _transition(_S.PLAN_APPROVAL, _E.AUTO_APPROVE, _S.TASK_LOOP),
    _transition(_S.PLAN_APPROVAL, _E.USER_OK, _S.TASK_LOOP),
    _transition(_S.TASK_LOOP, _E.NEXT_TASK, _S.INDEXING),
    _transition(_S.DESIGNING, _E.DESIGN_READY, _S.CODING),
    _transition(_S.CODING, _E.CODE_WRITTEN, _S.TESTING),
    _transition(_S.TESTING, _E.TESTS_PASS, _S.REVIEWING),
    _transition(_S.REVIEWING, _E.CHANGES_REQUESTED, _S.CODING),
    _transition(_S.REVIEWING, _E.APPROVED, _S.TASK_LOOP),
    _transition(_S.TASK_LOOP, _E.ALL_DONE, _S.INTEGRATION_TEST),
    _transition(_S.INTEGRATION_TEST, _E.INTEGRATION_PASS, _S.DEPLOYING),
    _transition(_S.DEPLOYING, _E.BUILT, _S.DONE),
)

_TRANSITION_LOOKUP: dict[tuple[OrchestratorState, str], OrchestratorState] = {
    (t.from_state, t.event): t.to_state for t in _TRANSITIONS
}


class Orchestrator:
    """Deterministic session orchestrator with persisted state."""

    MAX_TASK_RETRIES = 3
    PLANNING_RETRY_KEY = "__planning__"

    def __init__(
        self,
        workspace: Workspace,
        event_bus: EventBus | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.workspace = workspace
        self.event_bus = event_bus or EventBus(events_store=workspace.events_store())
        self.settings = settings or get_settings()
        self.session: SessionState | None = None

    def router(self) -> LLMRouter:
        from agent_builder.llm.router import LLMRouter

        return LLMRouter(
            self.settings,
            event_bus=self.event_bus,
            session_id=self.session.session_id if self.session else None,
        )

    async def execute_planning(self) -> Plan | None:
        """Run the Planner agent and transition to PLAN_APPROVAL or retry PLANNING."""
        if self.session is None:
            raise StateNotFoundError("No active session. Call start() or resume() first.")
        if self.session.current_state != OrchestratorState.PLANNING:
            raise StateTransitionError(
                f"execute_planning requires PLANNING, got {self.session.current_state}"
            )

        planner = PlannerAgent(self.router(), self.workspace)
        context = AgentContext(
            session_id=self.session.session_id,
            user_prompt=self.session.user_prompt,
            task_type="default",
        )
        result = await planner.run(context)

        plan = result.data.get("plan")
        if result.success and isinstance(plan, Plan):
            self.dispatch(
                OrchestratorEvent.PLAN_VALID,
                TransitionContext(plan=plan, payload={"project_name": plan.project_name}),
            )
            return plan

        self.dispatch(
            OrchestratorEvent.PLAN_INVALID,
            TransitionContext(
                payload={
                    "error": result.output or (result.errors[-1] if result.errors else "unknown"),
                    "attempts": result.attempts,
                },
            ),
        )
        return None

    def approve_plan(self) -> SessionState:
        """Auto-approve plan and enter the task loop (Fase 2 default)."""
        if self.session is None:
            raise StateNotFoundError("No active session. Call start() or resume() first.")
        plan = self.workspace.load_plan()
        if plan is None:
            raise StateTransitionError("No plan.json in workspace")
        return self.dispatch(
            OrchestratorEvent.AUTO_APPROVE,
            TransitionContext(plan=plan, task_id=plan.tasks[0].id if plan.tasks else None),
        )

    def _current_plan_task(self, plan: Plan) -> PlanTask | None:
        assert self.session is not None
        if not self.session.current_task:
            return None
        for task in plan.tasks:
            if task.id == self.session.current_task:
                return task
        return None

    def advance_task_loop(self) -> SessionState:
        """Pick the next ready task or finish when all tasks are done."""
        if self.session is None:
            raise StateNotFoundError("No active session")
        plan = self.workspace.load_plan()
        if plan is None:
            raise StateTransitionError("No plan.json in workspace")

        nxt = next_executable_task(plan, self.session.completed_tasks)
        if nxt is None:
            return self.dispatch(OrchestratorEvent.ALL_DONE)

        return self.dispatch(
            OrchestratorEvent.NEXT_TASK,
            TransitionContext(task_id=nxt.id, payload={"task_id": nxt.id}),
        )

    def complete_indexing(self, *, requires_design: bool = False) -> SessionState:
        """Stub indexer: jump to DESIGNING or CODING (Fase 3 will run real indexer)."""
        return self.dispatch(
            OrchestratorEvent.INDEXING_DONE,
            TransitionContext(requires_design=requires_design),
        )

    async def execute_coding(self) -> bool:
        """Run Coder for the current task and transition to TESTING."""
        if self.session is None:
            raise StateNotFoundError("No active session")
        if self.session.current_state != OrchestratorState.CODING:
            raise StateTransitionError(
                f"execute_coding requires CODING, got {self.session.current_state}"
            )

        plan = self.workspace.load_plan()
        if plan is None:
            raise StateTransitionError("No plan.json in workspace")

        plan_task = self._current_plan_task(plan)
        if plan_task is None:
            raise StateTransitionError("No current plan task")

        feedback = self._collect_retry_feedback(plan_task.id)
        coder = CoderAgent(self.router(), self.workspace)
        context = AgentContext(
            session_id=self.session.session_id,
            user_prompt=self.session.user_prompt,
            task_id=plan_task.id,
            task_title=plan_task.title,
            task_type=plan_task.type,
            extra={
                "plan": plan,
                "plan_task": plan_task,
                "feedback": feedback,
                "retry_count": self.session.get_task_retry_count(plan_task.id),
            },
        )
        result = await coder.run(context)

        if result.success:
            self.dispatch(
                OrchestratorEvent.CODE_WRITTEN,
                TransitionContext(
                    task_id=plan_task.id,
                    payload={"files": result.data.get("files", [])},
                ),
            )
            return True

        self.event_bus.publish_sync(
            Event(
                type=EventType.TASK_FAILED,
                session_id=self.session.session_id,
                payload={
                    "task_id": plan_task.id,
                    "error": result.output or result.errors,
                    "agent": "coder",
                },
            )
        )
        return False

    def _collect_retry_feedback(self, task_id: str) -> str:
        """Load test/review notes for Coder retries."""
        parts: list[str] = []
        test_path = self.workspace.test_result_path(task_id)
        if test_path.is_file():
            snippet = test_path.read_text(encoding="utf-8")[:4000]
            parts.append(f"Test failures ({task_id}):\n{snippet}")
        review_path = self.workspace.review_path(task_id)
        if review_path.is_file():
            snippet = review_path.read_text(encoding="utf-8")[:4000]
            parts.append(f"Review notes ({task_id}):\n{snippet}")
        return "\n\n".join(parts)

    async def execute_testing(self) -> bool:
        """Run Tester and transition to REVIEWING or back to CODING on failure."""
        if self.session is None:
            raise StateNotFoundError("No active session")
        if self.session.current_state != OrchestratorState.TESTING:
            raise StateTransitionError(
                f"execute_testing requires TESTING, got {self.session.current_state}"
            )

        plan = self.workspace.load_plan()
        if plan is None:
            raise StateTransitionError("No plan.json in workspace")
        plan_task = self._current_plan_task(plan)
        if plan_task is None:
            raise StateTransitionError("No current plan task")

        tester = TesterAgent(self.router(), self.workspace)
        context = AgentContext(
            session_id=self.session.session_id,
            user_prompt=self.session.user_prompt,
            task_id=plan_task.id,
            task_title=plan_task.title,
            extra={"plan_task": plan_task},
        )
        result = await tester.run(context)
        test_result = result.data.get("test_result")

        if result.success and isinstance(test_result, TesterReport):
            self.dispatch(
                OrchestratorEvent.TESTS_PASS,
                TransitionContext(task_id=plan_task.id, payload={"status": test_result.status}),
            )
            return True

        self.dispatch(
            OrchestratorEvent.TESTS_FAIL,
            TransitionContext(
                task_id=plan_task.id,
                payload={
                    "error": result.output,
                    "retry": self.session.get_task_retry_count(plan_task.id),
                },
            ),
        )
        return False

    async def execute_review(self) -> bool:
        """Run Reviewer and approve task or send changes back to CODING."""
        if self.session is None:
            raise StateNotFoundError("No active session")
        if self.session.current_state != OrchestratorState.REVIEWING:
            raise StateTransitionError(
                f"execute_review requires REVIEWING, got {self.session.current_state}"
            )

        plan = self.workspace.load_plan()
        if plan is None:
            raise StateTransitionError("No plan.json in workspace")
        plan_task = self._current_plan_task(plan)
        if plan_task is None:
            raise StateTransitionError("No current plan task")

        reviewer = ReviewerAgent(self.router(), self.workspace)
        context = AgentContext(
            session_id=self.session.session_id,
            user_prompt=self.session.user_prompt,
            task_id=plan_task.id,
            task_title=plan_task.title,
            extra={"plan": plan, "plan_task": plan_task},
        )
        result = await reviewer.run(context)
        review = result.data.get("review")

        if result.success and isinstance(review, ReviewResult):
            self.dispatch(
                OrchestratorEvent.APPROVED,
                TransitionContext(task_id=plan_task.id, payload={"verdict": review.verdict}),
            )
            return True

        if isinstance(review, ReviewResult) and review.requires_changes():
            self.dispatch(
                OrchestratorEvent.CHANGES_REQUESTED,
                TransitionContext(
                    task_id=plan_task.id,
                    payload={
                        "verdict": review.verdict,
                        "feedback": format_review_feedback(review),
                    },
                ),
            )
            return False

        self.dispatch(
            OrchestratorEvent.CHANGES_REQUESTED,
            TransitionContext(
                task_id=plan_task.id,
                payload={"error": result.output or "review failed"},
            ),
        )
        return False

    async def run_build_pipeline(self, *, auto_approve: bool = True) -> SessionState:
        """Plan, code all tasks, test, review, and finish the pipeline."""
        if self.session is None:
            raise StateNotFoundError("No active session")

        if self.session.current_state == OrchestratorState.PLANNING:
            plan = await self.execute_planning()
            if plan is None:
                return self.session

        if auto_approve and self.session.current_state == OrchestratorState.PLAN_APPROVAL:
            self.approve_plan()

        while self.session is not None and not self.session.is_terminal():
            state = OrchestratorState(self.session.current_state)

            if state == OrchestratorState.TASK_LOOP:
                self.advance_task_loop()
                continue

            if state == OrchestratorState.INDEXING:
                plan = self.workspace.load_plan()
                task = self._current_plan_task(plan) if plan else None
                requires_design = task is not None and task.type == "ui"
                self.complete_indexing(requires_design=requires_design)
                continue

            if state == OrchestratorState.DESIGNING:
                self.dispatch(OrchestratorEvent.DESIGN_READY)
                continue

            if state == OrchestratorState.CODING:
                ok = await self.execute_coding()
                if not ok:
                    break
                continue

            if state == OrchestratorState.TESTING:
                ok = await self.execute_testing()
                if not ok and self.session is not None:
                    if self.session.current_state == OrchestratorState.FAILED:
                        break
                    if self.session.current_state == OrchestratorState.CODING:
                        continue
                continue

            if state == OrchestratorState.REVIEWING:
                ok = await self.execute_review()
                if not ok and self.session is not None:
                    if self.session.current_state == OrchestratorState.CODING:
                        continue
                continue

            if state == OrchestratorState.INTEGRATION_TEST:
                self.dispatch(OrchestratorEvent.INTEGRATION_PASS)
                continue

            if state == OrchestratorState.DEPLOYING:
                self.dispatch(OrchestratorEvent.BUILT)
                continue

            break

        self.finalize_session_metrics()
        assert self.session is not None
        return self.session

    def finalize_session_metrics(self) -> None:
        """Persist LLM call count, cost, and elapsed time on the session."""
        from agent_builder.validation.project_output import (
            apply_metrics_to_session,
            summarize_metrics_from_events,
        )

        if self.session is None:
            return
        events = self.workspace.events_store().load_all()
        summary = summarize_metrics_from_events(events, self.session)
        apply_metrics_to_session(self.session, summary)
        self.persist()
        self.event_bus.publish_sync(
            Event(
                type=EventType.COST_UPDATED,
                session_id=self.session.session_id,
                payload={
                    "total_llm_calls": summary.total_llm_calls,
                    "total_cost_usd": summary.total_cost_usd,
                    "elapsed_seconds": summary.elapsed_seconds,
                    "input_tokens": summary.input_tokens,
                    "output_tokens": summary.output_tokens,
                },
            )
        )

    def resume(self) -> SessionState | None:
        """Load an in-progress session from disk."""
        self.session = self.workspace.load_session()
        return self.session

    def start(self, prompt: str) -> SessionState:
        """Begin a new session from ``IDLE`` with the user prompt."""
        self.workspace.ensure_layout()
        self.session = SessionState(user_prompt=prompt, current_state=OrchestratorState.IDLE)
        self.dispatch(OrchestratorEvent.PROMPT_RECEIVED)
        return self.session

    def dispatch(
        self,
        event: str,
        context: TransitionContext | None = None,
    ) -> SessionState:
        """Apply an event and persist the new orchestrator state."""
        if self.session is None:
            raise StateNotFoundError("No active session. Call start() or resume() first.")
        if self.session.is_terminal():
            raise StateTransitionError(
                f"Session {self.session.session_id} is terminal ({self.session.current_state})"
            )

        ctx = context or TransitionContext()
        current = OrchestratorState(self.session.current_state)
        next_state = resolve_next_state(current, event, self.session, ctx)
        if next_state is None:
            raise StateTransitionError(f"Invalid transition: {current.value} + {event}")

        previous = current
        self._apply_side_effects(previous, next_state, event, ctx)
        self.session.current_state = next_state
        self.persist()
        self._emit_state_changed(previous, next_state, event, ctx)
        return self.session

    def persist(self) -> None:
        if self.session is not None:
            self.workspace.save_session(self.session)

    def is_done(self) -> bool:
        return self.session is not None and self.session.current_state == OrchestratorState.DONE

    def _apply_side_effects(
        self,
        previous: OrchestratorState,
        next_state: OrchestratorState,
        event: str,
        ctx: TransitionContext,
    ) -> None:
        assert self.session is not None

        if event == OrchestratorEvent.PLAN_INVALID:
            self.session.increment_task_retry(self.PLANNING_RETRY_KEY)

        if event in (OrchestratorEvent.AUTO_APPROVE, OrchestratorEvent.USER_OK):
            if ctx.plan is not None and ctx.plan.tasks:
                self.session.current_task = ctx.plan.tasks[0].id
            elif ctx.task_id:
                self.session.current_task = ctx.task_id

        if event == OrchestratorEvent.NEXT_TASK and ctx.task_id:
            self.session.current_task = ctx.task_id

        if event == OrchestratorEvent.APPROVED and self.session.current_task:
            task_id = self.session.current_task
            if task_id not in self.session.completed_tasks:
                self.session.completed_tasks.append(task_id)

        if event == OrchestratorEvent.TESTS_FAIL and self.session.current_task:
            self.session.increment_task_retry(self.session.current_task)

        if event == OrchestratorEvent.PLAN_VALID and ctx.plan is not None:
            self.workspace.save_plan(ctx.plan)

    def _emit_state_changed(
        self,
        previous: OrchestratorState,
        next_state: OrchestratorState,
        event: str,
        ctx: TransitionContext,
    ) -> None:
        assert self.session is not None
        self.event_bus.publish_sync(
            Event(
                type=EventType.STATE_CHANGED,
                session_id=self.session.session_id,
                payload={
                    "from": previous.value,
                    "to": next_state.value,
                    "event": event,
                    "current_task": self.session.current_task,
                    **ctx.payload,
                },
            )
        )


def resolve_next_state(
    current: OrchestratorState,
    event: str,
    session: SessionState,
    ctx: TransitionContext,
) -> OrchestratorState | None:
    """Resolve the next FSM state, including conditional branches."""
    if current == OrchestratorState.INDEXING and event == OrchestratorEvent.INDEXING_DONE:
        return OrchestratorState.DESIGNING if ctx.requires_design else OrchestratorState.CODING

    if current == OrchestratorState.TESTING and event == OrchestratorEvent.TESTS_FAIL:
        task_id = session.current_task or ctx.task_id
        if task_id is None:
            return None
        retries = session.get_task_retry_count(task_id)
        if retries >= Orchestrator.MAX_TASK_RETRIES:
            return OrchestratorState.FAILED
        return OrchestratorState.CODING

    return _TRANSITION_LOOKUP.get((current, event))


def walk_happy_path(
    orch: Orchestrator,
    *,
    requires_design: bool = False,
    skip_planning: bool = False,
) -> SessionState:
    """Advance through a minimal IDLE → DONE path (for tests and smoke checks)."""
    if not skip_planning:
        orch.dispatch(OrchestratorEvent.PLAN_VALID)
    orch.dispatch(
        OrchestratorEvent.AUTO_APPROVE,
        TransitionContext(task_id="T1.1"),
    )
    orch.dispatch(OrchestratorEvent.NEXT_TASK, TransitionContext(task_id="T1.1"))
    orch.dispatch(
        OrchestratorEvent.INDEXING_DONE,
        TransitionContext(requires_design=requires_design),
    )
    if requires_design:
        orch.dispatch(OrchestratorEvent.DESIGN_READY)
    orch.dispatch(OrchestratorEvent.CODE_WRITTEN)
    orch.dispatch(OrchestratorEvent.TESTS_PASS)
    orch.dispatch(OrchestratorEvent.APPROVED)
    orch.dispatch(OrchestratorEvent.ALL_DONE)
    orch.dispatch(OrchestratorEvent.INTEGRATION_PASS)
    orch.dispatch(OrchestratorEvent.BUILT)
    assert orch.session is not None
    return orch.session
