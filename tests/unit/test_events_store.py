import json
from pathlib import Path

import pytest

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.events_store import EventsStore
from agent_builder.core.exceptions import WorkspaceError
from agent_builder.core.workspace import Workspace


def test_append_and_load_roundtrip(tmp_path: Path) -> None:
    store = EventsStore(tmp_path / "events.jsonl")
    event = Event(
        type=EventType.TASK_STARTED,
        session_id="session-abc",
        payload={"task_id": "T2.1", "agent": "coder"},
    )
    store.append(event)
    store.append(
        Event(
            type=EventType.LLM_CALL,
            session_id="session-abc",
            payload={"model": "sonnet", "input_tokens": 100},
        )
    )

    loaded = store.load_all()
    assert len(loaded) == 2
    assert loaded[0].type == EventType.TASK_STARTED
    assert loaded[0].payload["task_id"] == "T2.1"
    assert loaded[1].payload["model"] == "sonnet"


def test_jsonl_line_format_matches_architecture(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    store = EventsStore(path)
    store.append(
        Event(
            type=EventType.TASK_COMPLETED,
            session_id="s",
            payload={"task_id": "T2.1", "duration_s": 74},
        )
    )
    line = path.read_text(encoding="utf-8").strip()
    data = json.loads(line)
    assert data["type"] == "task_completed"
    assert data["task_id"] == "T2.1"
    assert data["duration_s"] == 74
    assert "ts" in data


def test_load_empty_when_missing(tmp_path: Path) -> None:
    store = EventsStore(tmp_path / "missing.jsonl")
    assert store.load_all() == []


def test_load_invalid_line_raises(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"type":"task_started"\n', encoding="utf-8")
    with pytest.raises(WorkspaceError):
        EventsStore(path).load_all()


def test_workspace_events_store_helper(workspace: Workspace) -> None:
    store = workspace.events_store()
    assert store.path == workspace.events_path
