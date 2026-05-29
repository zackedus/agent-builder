"""Aggregate LLM cost metrics from session and events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import Plan, SessionState
from agent_builder.dashboard.cost.budget import (
    BudgetLevel,
    budget_level_for_usage,
    budget_usage_percent,
)
from agent_builder.llm.cost_tracker import estimate_cost

USD_TO_IDR = 16_000.0


@dataclass(frozen=True)
class AgentCostRow:
    agent: str
    cost_usd: float
    calls: int
    input_tokens: int
    output_tokens: int
    primary_model: str


@dataclass(frozen=True)
class ModelCostRow:
    model: str
    cost_usd: float
    calls: int
    percent: float


@dataclass(frozen=True)
class TokenTableRow:
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    calls: int
    cost_usd: float


@dataclass(frozen=True)
class TrendPoint:
    minutes: float
    cumulative_usd: float


@dataclass(frozen=True)
class CostSummary:
    total_cost_usd: float
    total_cost_idr: float
    total_calls: int
    budget_cap: float | None
    budget_remaining: float | None
    budget_percent: float | None
    budget_level: BudgetLevel
    burn_rate_usd_per_min: float
    projected_total_usd: float | None
    by_agent: tuple[AgentCostRow, ...]
    by_model: tuple[ModelCostRow, ...]
    trend: tuple[TrendPoint, ...]
    table_rows: tuple[TokenTableRow, ...]


def aggregate_cost_data(
    events: list[Event],
    session: SessionState | None,
    plan: Plan | None,
    *,
    budget_cap: float | None = None,
) -> CostSummary:
    """Build cost breakdown structures from persisted events."""
    llm_events = [e for e in events if e.type == EventType.LLM_CALL]
    session_start = _session_start(session, llm_events)

    agent_stats: dict[str, dict[str, int | float | str]] = {}
    model_stats: dict[str, dict[str, int | float]] = {}
    table_key_stats: dict[tuple[str, str], dict[str, int | float]] = {}
    trend_points: list[TrendPoint] = []
    cumulative = 0.0

    for event in sorted(llm_events, key=lambda e: e.timestamp):
        agent = str(event.payload.get("agent", "unknown"))
        model = str(event.payload.get("model", "ollama"))
        input_tokens = int(event.payload.get("input_tokens", 0))
        output_tokens = int(event.payload.get("output_tokens", 0))
        cost = estimate_cost(model, input_tokens, output_tokens)

        _accumulate(
            agent_stats,
            agent,
            cost,
            input_tokens,
            output_tokens,
            model,
        )
        _accumulate_model(model_stats, model, cost, input_tokens, output_tokens)
        key = (agent, model)
        if key not in table_key_stats:
            table_key_stats[key] = {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            }
        row = table_key_stats[key]
        row["calls"] = int(row["calls"]) + 1
        row["input_tokens"] = int(row["input_tokens"]) + input_tokens
        row["output_tokens"] = int(row["output_tokens"]) + output_tokens
        row["cost_usd"] = float(row["cost_usd"]) + cost

        cumulative += cost
        minutes = _minutes_since(session_start, event.timestamp)
        trend_points.append(TrendPoint(minutes=minutes, cumulative_usd=cumulative))

    total_cost = cumulative
    if session and session.metrics.total_cost_usd > total_cost:
        total_cost = session.metrics.total_cost_usd

    total_calls = len(llm_events)
    if session and session.metrics.total_llm_calls > total_calls:
        total_calls = session.metrics.total_llm_calls

    by_agent = _build_agent_rows(agent_stats, total_cost)
    by_model = _build_model_rows(model_stats, total_cost)
    table_rows = tuple(
        TokenTableRow(
            agent=agent,
            model=model,
            input_tokens=int(stats["input_tokens"]),
            output_tokens=int(stats["output_tokens"]),
            calls=int(stats["calls"]),
            cost_usd=float(stats["cost_usd"]),
        )
        for (agent, model), stats in sorted(
            table_key_stats.items(),
            key=lambda item: float(item[1]["cost_usd"]),
            reverse=True,
        )
    )

    elapsed_min = _elapsed_minutes(session, session_start)
    burn_rate = total_cost / max(elapsed_min, 0.1)
    projected = _project_total_cost(total_cost, session, plan)

    remaining = None
    if budget_cap is not None:
        remaining = max(0.0, budget_cap - total_cost)

    return CostSummary(
        total_cost_usd=total_cost,
        total_cost_idr=total_cost * USD_TO_IDR,
        total_calls=total_calls,
        budget_cap=budget_cap,
        budget_remaining=remaining,
        budget_percent=budget_usage_percent(total_cost, budget_cap),
        budget_level=budget_level_for_usage(total_cost, budget_cap),
        burn_rate_usd_per_min=burn_rate,
        projected_total_usd=projected,
        by_agent=by_agent,
        by_model=by_model,
        trend=tuple(trend_points),
        table_rows=table_rows,
    )


def _session_start(session: SessionState | None, llm_events: list[Event]) -> datetime:
    if session is not None:
        started = session.started_at
        if started.tzinfo is None:
            return started.replace(tzinfo=UTC)
        return started
    if llm_events:
        first = llm_events[0].timestamp
        if first.tzinfo is None:
            return first.replace(tzinfo=UTC)
        return first
    return datetime.now(UTC)


def _minutes_since(start: datetime, moment: datetime) -> float:
    a = moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    b = start if start.tzinfo else start.replace(tzinfo=UTC)
    return max(0.0, (a - b).total_seconds() / 60.0)


def _elapsed_minutes(session: SessionState | None, start: datetime) -> float:
    if session and session.metrics.elapsed_seconds:
        return max(session.metrics.elapsed_seconds / 60.0, 0.1)
    return max(_minutes_since(start, datetime.now(UTC)), 0.1)


def _project_total_cost(
    total_cost: float,
    session: SessionState | None,
    plan: Plan | None,
) -> float | None:
    if session is None or plan is None or not plan.tasks:
        return None
    completed = len(session.completed_tasks)
    total_tasks = len(plan.tasks)
    if completed <= 0:
        return None
    return total_cost * (total_tasks / completed)


def _accumulate(
    stats: dict[str, dict[str, int | float | str]],
    agent: str,
    cost: float,
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> None:
    if agent not in stats:
        stats[agent] = {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "primary_model": model,
        }
    row = stats[agent]
    row["calls"] = int(row["calls"]) + 1
    row["input_tokens"] = int(row["input_tokens"]) + input_tokens
    row["output_tokens"] = int(row["output_tokens"]) + output_tokens
    row["cost_usd"] = float(row["cost_usd"]) + cost
    if cost > 0:
        row["primary_model"] = model


def _accumulate_model(
    stats: dict[str, dict[str, int | float]],
    model: str,
    cost: float,
    input_tokens: int,
    output_tokens: int,
) -> None:
    if model not in stats:
        stats[model] = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    row = stats[model]
    row["calls"] = int(row["calls"]) + 1
    row["input_tokens"] = int(row["input_tokens"]) + input_tokens
    row["output_tokens"] = int(row["output_tokens"]) + output_tokens
    row["cost_usd"] = float(row["cost_usd"]) + cost


def _build_agent_rows(
    stats: dict[str, dict[str, int | float | str]],
    total_cost: float,
) -> tuple[AgentCostRow, ...]:
    rows = [
        AgentCostRow(
            agent=agent,
            cost_usd=float(data["cost_usd"]),
            calls=int(data["calls"]),
            input_tokens=int(data["input_tokens"]),
            output_tokens=int(data["output_tokens"]),
            primary_model=str(data["primary_model"]),
        )
        for agent, data in stats.items()
    ]
    rows.sort(key=lambda row: row.cost_usd, reverse=True)
    return tuple(rows)


def _build_model_rows(
    stats: dict[str, dict[str, int | float]],
    total_cost: float,
) -> tuple[ModelCostRow, ...]:
    rows = [
        ModelCostRow(
            model=model,
            cost_usd=float(data["cost_usd"]),
            calls=int(data["calls"]),
            percent=(float(data["cost_usd"]) / total_cost * 100.0) if total_cost else 0.0,
        )
        for model, data in stats.items()
    ]
    rows.sort(key=lambda row: row.cost_usd, reverse=True)
    return tuple(rows)
