"""Append-only event log (``events.jsonl``) for replay and audit."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agent_builder.core.event_bus import Event
from agent_builder.core.exceptions import WorkspaceError


class EventsStore:
    """Append-only JSONL store backed by ``workspace/.agent/events.jsonl``."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    def append(self, event: Event) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = event.to_jsonl_line() + "\n"
        try:
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise WorkspaceError(f"Failed to append event log: {self.path}") from exc

    def load_all(self) -> list[Event]:
        if not self.path.is_file():
            return []
        events: list[Event] = []
        try:
            for line_no, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    data: dict[str, Any] = json.loads(stripped)
                    events.append(Event.from_jsonl_dict(data))
                except (json.JSONDecodeError, ValueError, KeyError) as exc:
                    raise WorkspaceError(
                        f"Invalid event log line {line_no} in {self.path}"
                    ) from exc
        except OSError as exc:
            raise WorkspaceError(f"Failed to read event log: {self.path}") from exc
        return events

    def clear(self) -> None:
        if self.path.is_file():
            self.path.unlink()
