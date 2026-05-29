"""Unit tests for replay bookmarks."""

from __future__ import annotations

from agent_builder.core.event_bus import Event, EventType
from agent_builder.replay.bookmarks import compute_bookmarks


def test_compute_bookmarks_task_failed() -> None:
    events = [
        Event(
            type=EventType.TASK_FAILED,
            session_id="s",
            payload={"task_id": "T2.1", "error": "boom"},
        ),
    ]
    marks = compute_bookmarks(events)
    assert len(marks) == 1
    assert marks[0].category == "failure"
    assert "T2.1" in marks[0].label
