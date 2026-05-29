"""Budget threshold helpers shared by CostTracker and dashboard."""

from __future__ import annotations

from enum import StrEnum


class BudgetLevel(StrEnum):
    OK = "ok"
    WARN_50 = "warn_50"
    WARN_80 = "warn_80"
    EXCEEDED = "exceeded"


def budget_level_for_usage(spent_usd: float, budget_cap: float | None) -> BudgetLevel:
    """Map spend ratio to alert level (50% / 80% / 100%)."""
    if budget_cap is None or budget_cap <= 0:
        return BudgetLevel.OK
    ratio = spent_usd / budget_cap
    if ratio >= 1.0:
        return BudgetLevel.EXCEEDED
    if ratio >= 0.8:
        return BudgetLevel.WARN_80
    if ratio >= 0.5:
        return BudgetLevel.WARN_50
    return BudgetLevel.OK


def budget_usage_percent(spent_usd: float, budget_cap: float | None) -> float | None:
    if budget_cap is None or budget_cap <= 0:
        return None
    return min(100.0, (spent_usd / budget_cap) * 100.0)
