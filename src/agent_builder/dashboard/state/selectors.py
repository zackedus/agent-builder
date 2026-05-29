"""Computed dashboard views from session and events."""

from __future__ import annotations

from dataclasses import dataclass

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import Plan, SessionState


@dataclass(frozen=True)
class DashboardMetrics:
    progress_label: str
    llm_calls: int
    cost_usd: float
    retry_count: int
    orchestrator_state: str


def compute_metrics(
    session: SessionState | None,
    plan: Plan | None,
    events: list[Event],
) -> DashboardMetrics:
    """Build header metric chips for the dashboard shell."""
    total_tasks = len(plan.tasks) if plan else len(session.tasks) if session else 0
    completed = len(session.completed_tasks) if session else 0
    progress = f"{completed}/{total_tasks}" if total_tasks else f"{completed}/—"

    llm_calls = sum(1 for event in events if event.type == EventType.LLM_CALL)
    cost = session.metrics.total_cost_usd if session else 0.0
    retries = sum(session.retry_count.values()) if session else 0
    state = str(session.current_state) if session else "IDLE"

    if session and session.metrics.total_llm_calls:
        llm_calls = max(llm_calls, session.metrics.total_llm_calls)

    return DashboardMetrics(
        progress_label=progress,
        llm_calls=llm_calls,
        cost_usd=cost,
        retry_count=retries,
        orchestrator_state=state,
    )
