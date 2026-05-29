"""Unit tests for dashboard selectors."""

from __future__ import annotations

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import Plan, PlanTask, SessionMetrics, SessionState
from agent_builder.dashboard.components.activity_feed import format_event_line
from agent_builder.dashboard.state.selectors import compute_metrics
from agent_builder.dashboard.theme import agent_color, tokens_for_mode


def test_compute_metrics_from_session_and_events() -> None:
    session = SessionState(
        completed_tasks=["T1.1"],
        metrics=SessionMetrics(total_llm_calls=2, total_cost_usd=1.25),
        retry_count={"T1.1": 1},
    )
    plan = Plan(
        project_name="demo",
        description="x",
        tasks=[
            PlanTask(id="T1.1", title="A", type="logic"),
            PlanTask(id="T2.1", title="B", type="ui"),
        ],
    )
    events = [
        Event(type=EventType.LLM_CALL, session_id="s", payload={"model": "sonnet"}),
    ]
    metrics = compute_metrics(session, plan, events)
    assert metrics.progress_label == "1/2"
    assert metrics.llm_calls == 2
    assert metrics.cost_usd == 1.25
    assert metrics.retry_count == 1


def test_format_event_line_state_changed() -> None:
    event = Event(
        type=EventType.STATE_CHANGED,
        session_id="s",
        payload={"from": "CODING", "to": "TESTING"},
    )
    line = format_event_line(event)
    assert "state changed" in line.lower()
    assert "CODING" in line


def test_theme_tokens_and_agent_color() -> None:
    assert tokens_for_mode(dark=True).surface != tokens_for_mode(dark=False).surface
    assert agent_color("coder")["fg"] == "#0C447C"
