"""Unit tests for budget thresholds."""

from __future__ import annotations

from agent_builder.llm.budget import BudgetLevel, budget_level_for_usage, budget_usage_percent


def test_budget_level_thresholds() -> None:
    assert budget_level_for_usage(5.0, 10.0) == BudgetLevel.WARN_50
    assert budget_level_for_usage(8.0, 10.0) == BudgetLevel.WARN_80
    assert budget_level_for_usage(10.0, 10.0) == BudgetLevel.EXCEEDED
    assert budget_level_for_usage(1.0, None) == BudgetLevel.OK


def test_budget_usage_percent_caps_at_100() -> None:
    assert budget_usage_percent(12.0, 10.0) == 100.0
