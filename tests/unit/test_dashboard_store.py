"""Unit tests for dashboard store."""

from __future__ import annotations

from pathlib import Path

from agent_builder.core.event_bus import Event, EventBus, EventType
from agent_builder.core.state import OrchestratorState, SessionState
from agent_builder.core.workspace import Workspace
from agent_builder.dashboard.state.store import DashboardStore


def test_dashboard_store_refresh_and_subscribe(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "dash_ws")
    ws.ensure_layout()
    session = SessionState(user_prompt="Expense tracker", current_state=OrchestratorState.PLANNING)
    ws.save_session(session)

    store = DashboardStore(ws)
    calls = 0

    def listener() -> None:
        nonlocal calls
        calls += 1

    store.subscribe(listener)
    store.refresh()

    assert store.session is not None
    assert store.session.user_prompt == "Expense tracker"
    assert calls >= 1


def test_dashboard_store_ingests_event_bus() -> None:
    bus = EventBus()
    ws = Workspace(Path("unused"))
    store = DashboardStore(ws)
    store.attach_event_bus(bus)

    notified = 0

    def listener() -> None:
        nonlocal notified
        notified += 1

    store.subscribe(listener)
    bus.publish_sync(
        Event(
            type=EventType.AGENT_LOG,
            session_id="s1",
            payload={"message": "hello"},
        )
    )
    assert len(store.events) == 1
    assert notified >= 1


def test_toggle_dark_mode() -> None:
    store = DashboardStore(Workspace(Path("unused2")))
    assert store.dark_mode is False
    assert store.toggle_dark_mode() is True
    assert store.dark_mode is True


def test_select_task() -> None:
    store = DashboardStore(Workspace(Path("unused3")))
    assert store.selected_task_id is None
    store.select_task("T1.1")
    assert store.selected_task_id == "T1.1"
    store.select_task("T1.1")
    store.select_task(None)
    assert store.selected_task_id is None


def test_graph_filters_and_zoom() -> None:
    store = DashboardStore(Workspace(Path("unused4")))
    store.set_graph_filters(status="running", agent="coder", show_completed=False)
    assert store.graph_status_filter == "running"
    assert store.graph_agent_filter == "coder"
    assert store.graph_show_completed is False
    store.set_graph_zoom(3.0)
    assert store.graph_zoom == 2.5
    store.adjust_graph_pan(10.0, -5.0)
    assert store.graph_pan_x == 10.0
    assert store.graph_pan_y == -5.0
    store.reset_graph_view()
    assert store.graph_zoom == 1.0
    assert store.graph_pan_x == 0.0
