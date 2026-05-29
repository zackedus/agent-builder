"""Replay timeline clock formatting."""

from __future__ import annotations

from datetime import UTC, datetime

from agent_builder.core.event_bus import Event


def replay_clock(events: list[Event], position: int) -> str:
    """Format elapsed MM:SS at *position* (0 = start)."""
    if not events:
        return "00:00"
    start = _aware(events[0].timestamp)
    if position <= 0:
        return "00:00"
    index = min(position - 1, len(events) - 1)
    at = _aware(events[index].timestamp)
    seconds = max(0, int((at - start).total_seconds()))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def replay_duration_clock(events: list[Event]) -> str:
    return replay_clock(events, len(events))


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment
