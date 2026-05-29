"""Unit tests for SessionReplayer navigation."""

from __future__ import annotations

from agent_builder.core.event_bus import Event, EventType
from agent_builder.replay.player import SessionReplayer


def test_session_replayer_step_and_jump() -> None:
    events = [
        Event(type=EventType.STATE_CHANGED, session_id="s", payload={"to": "PLANNING"}),
        Event(type=EventType.STATE_CHANGED, session_id="s", payload={"to": "CODING"}),
        Event(type=EventType.TASK_FAILED, session_id="s", payload={"task_id": "T1"}),
    ]
    player = SessionReplayer(events)
    assert player.position == 3
    player.set_position(0)
    assert player.frame().position == 0
    player.step_forward()
    assert player.position == 1
    target = player.jump_to_next_event_type(EventType.TASK_FAILED)
    assert target is not None
    assert player.position == 3
