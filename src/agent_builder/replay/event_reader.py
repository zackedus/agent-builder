"""Load persisted session events for replay."""

from __future__ import annotations

from pathlib import Path

from agent_builder.core.event_bus import Event
from agent_builder.core.events_store import EventsStore
from agent_builder.core.workspace import Workspace


def load_events_from_path(path: Path) -> list[Event]:
    """Read all events from a JSONL file."""
    return EventsStore(path).load_all()


def load_events(workspace: Workspace) -> list[Event]:
    """Load events from the workspace ``events.jsonl``."""
    return workspace.events_store().load_all()
