"""Unit tests for dashboard cost aggregation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import Plan, PlanTask, SessionState
from agent_builder.dashboard.cost.aggregates import aggregate_cost_data
from agent_builder.llm.budget import BudgetLevel
from agent_builder.llm.router import SONNET_ALIAS


def test_aggregate_cost_data_from_events() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    events = [
        Event(
            type=EventType.LLM_CALL,
            session_id="s",
            timestamp=start,
            payload={
                "agent": "coder",
                "model": SONNET_ALIAS,
                "input_tokens": 1000,
                "output_tokens": 500,
            },
        ),
        Event(
            type=EventType.LLM_CALL,
            session_id="s",
            timestamp=start + timedelta(minutes=2),
            payload={
                "agent": "planner",
                "model": SONNET_ALIAS,
                "input_tokens": 2000,
                "output_tokens": 1000,
            },
        ),
    ]
    session = SessionState(started_at=start)
    plan = Plan(
        project_name="x",
        description="d",
        tasks=[PlanTask(id="T1", title="A", type="logic")],
    )
    summary = aggregate_cost_data(events, session, plan, budget_cap=10.0)
    assert summary.total_calls == 2
    assert summary.total_cost_usd > 0
    assert len(summary.by_agent) == 2
    assert len(summary.trend) == 2
    assert summary.budget_level == BudgetLevel.OK


def test_aggregate_cost_data_projected_total() -> None:
    session = SessionState(completed_tasks=["T1"])
    plan = Plan(
        project_name="x",
        description="d",
        tasks=[
            PlanTask(id="T1", title="A", type="logic"),
            PlanTask(id="T2", title="B", type="logic"),
        ],
    )
    events = [
        Event(
            type=EventType.LLM_CALL,
            session_id="s",
            payload={
                "agent": "coder",
                "model": SONNET_ALIAS,
                "input_tokens": 1000,
                "output_tokens": 0,
            },
        ),
    ]
    summary = aggregate_cost_data(events, session, plan)
    assert summary.projected_total_usd is not None
    assert summary.projected_total_usd >= summary.total_cost_usd
