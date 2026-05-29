"""Deterministic session state from event log (event sourcing)."""

from __future__ import annotations

from dataclasses import dataclass

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import OrchestratorState, SessionMetrics, SessionState
from agent_builder.llm.cost_tracker import estimate_cost


@dataclass(frozen=True)
class ReplayFrame:
    """Snapshot after applying events up to *position*."""

    position: int
    state: SessionState
    last_event: Event | None
    cumulative_cost_usd: float


def initial_replay_session(base: SessionState | None) -> SessionState:
    """Seed replay from workspace session metadata without runtime progress."""
    if base is None:
        return SessionState(current_state=OrchestratorState.IDLE)
    return SessionState(
        session_id=base.session_id,
        started_at=base.started_at,
        user_prompt=base.user_prompt,
        current_state=OrchestratorState.IDLE,
        current_task=None,
        completed_tasks=[],
        failed_tasks=[],
        retry_count={},
        metrics=SessionMetrics(),
        tasks=list(base.tasks),
    )


def apply_event(state: SessionState, event: Event) -> SessionState:
    """Pure fold step: return new session after *event*."""
    session = state.model_copy(deep=True)

    if event.type == EventType.STATE_CHANGED:
        raw_to = event.payload.get("to")
        if isinstance(raw_to, str) and raw_to:
            session.current_state = OrchestratorState(raw_to)
        task_id = event.payload.get("current_task")
        if isinstance(task_id, str) and task_id:
            session.current_task = task_id

    elif event.type == EventType.TASK_STARTED:
        task_id = event.payload.get("task_id")
        if isinstance(task_id, str) and task_id:
            session.current_task = task_id

    elif event.type == EventType.TASK_COMPLETED:
        task_id = event.payload.get("task_id")
        if isinstance(task_id, str) and task_id and task_id not in session.completed_tasks:
            session.completed_tasks.append(task_id)

    elif event.type == EventType.TASK_FAILED:
        task_id = event.payload.get("task_id")
        if isinstance(task_id, str) and task_id:
            if task_id not in session.failed_tasks:
                session.failed_tasks.append(task_id)
            session.current_task = task_id
            session.increment_task_retry(task_id)

    elif event.type == EventType.TASK_BLOCKED:
        task_id = event.payload.get("task_id")
        if isinstance(task_id, str) and task_id:
            session.current_task = task_id
            session.increment_task_retry(task_id)

    elif event.type == EventType.LLM_CALL:
        model = str(event.payload.get("model", "ollama"))
        input_tokens = int(event.payload.get("input_tokens", 0))
        output_tokens = int(event.payload.get("output_tokens", 0))
        session.metrics.total_llm_calls += 1
        session.metrics.total_cost_usd += estimate_cost(model, input_tokens, output_tokens)

    elif event.type == EventType.COST_UPDATED:
        total = event.payload.get("total_cost_usd")
        if total is not None:
            session.metrics.total_cost_usd = float(total)

    return session


def reconstruct_at(
    events: list[Event],
    position: int,
    base: SessionState | None = None,
) -> ReplayFrame:
    """Apply ``events[:position]`` and return the resulting frame."""
    pos = max(0, min(len(events), position))
    state = initial_replay_session(base)
    last: Event | None = None
    for event in events[:pos]:
        state = apply_event(state, event)
        last = event
    return ReplayFrame(
        position=pos,
        state=state,
        last_event=last,
        cumulative_cost_usd=state.metrics.total_cost_usd,
    )
