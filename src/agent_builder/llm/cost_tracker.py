"""Token cost tracking via event bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from agent_builder.core.event_bus import Event, EventBus, EventType
from agent_builder.llm.budget import BudgetLevel, budget_level_for_usage
from agent_builder.llm.types import LLMResponse

# USD per 1M tokens (ARCHITECTURE.md §17.4)
PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-7": {"in": 15.0, "out": 75.0},
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0},
    "ollama": {"in": 0.0, "out": 0.0},
}


@dataclass
class CostRecord:
    agent: str
    model: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


def estimate_cost(model_alias: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING.get(model_alias, {"in": 0.0, "out": 0.0})
    return (input_tokens * rates["in"] + output_tokens * rates["out"]) / 1_000_000


class CostTracker:
    """Accumulates LLM spend from ``llm_call`` events."""

    def __init__(self, event_bus: EventBus, budget_cap: float | None = None) -> None:
        self.records: list[CostRecord] = []
        self.budget_cap = budget_cap
        self._budget_exceeded = False
        self._budget_level = BudgetLevel.OK
        self._pause_all = False
        self._pause_planner = False
        self._event_bus = event_bus
        event_bus.subscribe(EventType.LLM_CALL, self.on_llm_call)

    @property
    def total_cost_usd(self) -> float:
        return sum(record.cost_usd for record in self.records)

    @property
    def budget_exceeded(self) -> bool:
        return self._budget_exceeded

    @property
    def budget_level(self) -> BudgetLevel:
        return self._budget_level

    @property
    def pause_all_agents(self) -> bool:
        return self._pause_all

    @property
    def pause_planner(self) -> bool:
        return self._pause_planner

    def should_allow_call(self, agent: str) -> bool:
        """Enforce budget thresholds (80% planner pause, 100% all pause)."""
        if self.budget_cap is None:
            return True
        if self._pause_all:
            return False
        if self._pause_planner and agent.lower() == "planner":
            return False
        return True

    def on_llm_call(self, event: Event) -> None:
        model = str(event.payload.get("model", "ollama"))
        agent = str(event.payload.get("agent", "unknown"))
        input_tokens = int(event.payload.get("input_tokens", 0))
        output_tokens = int(event.payload.get("output_tokens", 0))
        cost = estimate_cost(model, input_tokens, output_tokens)
        self.records.append(
            CostRecord(
                agent=agent,
                model=model,
                cost_usd=cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                timestamp=event.timestamp,
            )
        )
        self._check_budget()

    def record_response(self, agent: str, response: LLMResponse) -> CostRecord:
        """Record cost directly without going through the event bus."""
        cost = estimate_cost(
            response.model,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        record = CostRecord(
            agent=agent,
            model=response.model,
            cost_usd=cost,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        self.records.append(record)
        self._check_budget()
        return record

    def _check_budget(self) -> None:
        if self.budget_cap is None:
            return
        level = budget_level_for_usage(self.total_cost_usd, self.budget_cap)
        self._budget_level = level
        self._pause_planner = level in (BudgetLevel.WARN_80, BudgetLevel.EXCEEDED)
        self._pause_all = level == BudgetLevel.EXCEEDED
        self._budget_exceeded = self._pause_all
        self._publish_cost_update()

    def _publish_cost_update(self) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish_sync(
            Event(
                type=EventType.COST_UPDATED,
                session_id="",
                payload={
                    "total_cost_usd": self.total_cost_usd,
                    "budget_cap": self.budget_cap,
                    "budget_level": self._budget_level.value,
                    "pause_all": self._pause_all,
                    "pause_planner": self._pause_planner,
                },
            ),
        )
