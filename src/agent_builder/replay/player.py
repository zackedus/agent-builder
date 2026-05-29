"""Session replay controller over an event list."""

from __future__ import annotations

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import SessionState
from agent_builder.replay.bookmarks import ReplayBookmark, compute_bookmarks
from agent_builder.replay.state_reconstruction import ReplayFrame, reconstruct_at

REPLAY_SPEEDS = (0.5, 1.0, 2.0, 5.0, 10.0)

JUMP_EVENT_TYPES: tuple[tuple[str, EventType], ...] = (
    ("Task started", EventType.TASK_STARTED),
    ("Task completed", EventType.TASK_COMPLETED),
    ("Task failed", EventType.TASK_FAILED),
    ("State changed", EventType.STATE_CHANGED),
    ("LLM call", EventType.LLM_CALL),
)


class SessionReplayer:
    """Navigate and reconstruct state at any point in the event log."""

    def __init__(
        self,
        events: list[Event],
        base_session: SessionState | None = None,
    ) -> None:
        self.events = list(events)
        self.base_session = base_session
        self.position = len(self.events)
        self.bookmarks: list[ReplayBookmark] = compute_bookmarks(self.events)

    @property
    def at_live_tail(self) -> bool:
        return self.position >= len(self.events)

    def frame(self) -> ReplayFrame:
        return reconstruct_at(self.events, self.position, self.base_session)

    def set_position(self, position: int) -> ReplayFrame:
        self.position = max(0, min(len(self.events), position))
        return self.frame()

    def step_back(self) -> ReplayFrame:
        return self.set_position(self.position - 1)

    def step_forward(self) -> ReplayFrame:
        return self.set_position(self.position + 1)

    def jump_to_start(self) -> ReplayFrame:
        return self.set_position(0)

    def jump_to_end(self) -> ReplayFrame:
        return self.set_position(len(self.events))

    def jump_to_bookmark(self, bookmark: ReplayBookmark) -> ReplayFrame:
        return self.set_position(bookmark.position)

    def find_next_event_type(self, event_type: EventType) -> int | None:
        """Return 1-based position of next matching event after current position."""
        for index in range(self.position, len(self.events)):
            if self.events[index].type == event_type:
                return index + 1
        return None

    def jump_to_next_event_type(self, event_type: EventType) -> ReplayFrame | None:
        target = self.find_next_event_type(event_type)
        if target is None:
            return None
        return self.set_position(target)
