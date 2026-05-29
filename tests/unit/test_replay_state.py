"""Unit tests for replay state reconstruction."""

from __future__ import annotations

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import OrchestratorState, SessionState
from agent_builder.replay.state_reconstruction import apply_event, reconstruct_at


def test_apply_event_state_changed() -> None:
    session = SessionState(current_state=OrchestratorState.IDLE)
    updated = apply_event(
        session,
        Event(
            type=EventType.STATE_CHANGED,
            session_id="s",
            payload={"from": "IDLE", "to": "CODING", "current_task": "T1"},
        ),
    )
    assert updated.current_state == OrchestratorState.CODING
    assert updated.current_task == "T1"


def test_reconstruct_at_cumulative_cost() -> None:
    events = [
        Event(
            type=EventType.LLM_CALL,
            session_id="s",
            payload={
                "agent": "coder",
                "model": "claude-sonnet-4-6",
                "input_tokens": 1000,
                "output_tokens": 0,
            },
        ),
        Event(
            type=EventType.STATE_CHANGED,
            session_id="s",
            payload={"from": "CODING", "to": "TESTING"},
        ),
    ]
    frame = reconstruct_at(events, 1)
    assert frame.position == 1
    assert frame.cumulative_cost_usd > 0
    assert frame.last_event is not None
    assert frame.last_event.type == EventType.LLM_CALL

    full = reconstruct_at(events, 2)
    assert full.state.current_state == OrchestratorState.TESTING
