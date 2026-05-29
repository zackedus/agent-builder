"""Unit tests for dashboard replay store integration."""

from __future__ import annotations

from pathlib import Path

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import SessionState
from agent_builder.core.workspace import Workspace
from agent_builder.dashboard.state.store import DashboardStore


def test_session_for_views_uses_replay_snapshot(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "replay_ws")
    ws.ensure_layout()
    session = SessionState(user_prompt="demo", current_state="DONE")
    ws.save_session(session)

    store = DashboardStore(ws)
    store.events = [
        Event(
            type=EventType.STATE_CHANGED,
            session_id=session.session_id,
            payload={"from": "IDLE", "to": "PLANNING"},
        ),
        Event(
            type=EventType.STATE_CHANGED,
            session_id=session.session_id,
            payload={"from": "PLANNING", "to": "CODING"},
        ),
    ]
    store._replayer = None
    store.set_replay_position(1)
    view_session = store.session_for_views()
    assert view_session is not None
    assert str(view_session.current_state) == "PLANNING"
    assert len(store.events_for_views()) == 1
