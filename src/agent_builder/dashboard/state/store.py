"""Observable dashboard store backed by workspace files and optional event bus."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_builder.core.event_bus import Event, EventBus, EventType
from agent_builder.core.state import OrchestratorState, Plan, SessionState
from agent_builder.core.workspace import Workspace
from agent_builder.dashboard.state.selectors import DashboardMetrics, compute_metrics

Listener = Callable[[], None]


class DashboardStore:
    """Holds dashboard state and notifies UI subscribers on change."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.session: SessionState | None = None
        self.plan: Plan | None = None
        self.events: list[Event] = []
        self.dark_mode: bool = False
        self.active_tab: int = 0
        self.selected_task_id: str | None = None
        self._listeners: list[Listener] = []
        self._event_bus: EventBus | None = None

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def set_active_tab(self, index: int) -> None:
        if index == self.active_tab:
            return
        self.active_tab = index
        self._notify()

    def select_task(self, task_id: str | None) -> None:
        if task_id == self.selected_task_id:
            return
        self.selected_task_id = task_id
        self._notify()

    def toggle_dark_mode(self) -> bool:
        self.dark_mode = not self.dark_mode
        self._notify()
        return self.dark_mode

    def metrics(self) -> DashboardMetrics:
        return compute_metrics(self.session, self.plan, self.events)

    def refresh(self) -> None:
        """Reload session, plan, and events from disk."""
        self.session = self.workspace.load_session()
        self.plan = self.workspace.load_plan()
        self.events = self.workspace.events_store().load_all()
        self._notify()

    def attach_event_bus(self, bus: EventBus) -> None:
        """Subscribe to live orchestrator events (in-process dashboard)."""
        self._event_bus = bus

        def _on_event(event: Event) -> None:
            self._ingest_event(event)

        bus.subscribe_all(_on_event)

    def _ingest_event(self, event: Event) -> None:
        self.events.append(event)
        if len(self.events) > 2_000:
            self.events = self.events[-2_000:]
        if self.session is not None and event.session_id == self.session.session_id:
            if event.type == EventType.STATE_CHANGED:
                raw = event.payload.get("to")
                if isinstance(raw, str) and raw:
                    self.session.current_state = OrchestratorState(raw)
        self._notify()

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()


def open_store(workspace_dir: Path | None = None) -> DashboardStore:
    from agent_builder.config import get_settings

    settings = get_settings()
    root = workspace_dir or settings.workspace_dir
    workspace = Workspace(root)
    workspace.ensure_layout()
    store = DashboardStore(workspace)
    store.refresh()
    return store
