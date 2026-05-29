"""Tab 3 — Cost breakdown with metrics, charts, and budget alerts."""

from __future__ import annotations

from typing import Any

from agent_builder.config import get_settings
from agent_builder.dashboard.components.cost_charts import (
    build_agent_bar_chart,
    build_budget_banner,
    build_cost_metrics_row,
    build_cost_trend_chart,
    build_model_breakdown,
    build_token_usage_table,
)
from agent_builder.dashboard.cost.aggregates import aggregate_cost_data
from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens


def build_cost_view(store: DashboardStore, tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    budget_cap = get_settings().budget_usd
    summary = aggregate_cost_data(
        store.events,
        store.session,
        store.plan,
        budget_cap=budget_cap,
    )

    banner = build_budget_banner(summary, tokens)
    metrics = build_cost_metrics_row(summary, tokens)
    agent_chart = build_agent_bar_chart(summary.by_agent, summary.total_cost_usd, tokens)
    model_chart = build_model_breakdown(summary.by_model, tokens)
    trend = build_cost_trend_chart(
        summary.trend,
        tokens,
        projected_total=summary.projected_total_usd,
    )
    table = build_token_usage_table(summary.table_rows, tokens)

    sections: list[Any] = [
        ft.Text("Cost breakdown", size=18, weight=ft.FontWeight.BOLD),
    ]
    if banner is not None:
        sections.append(banner)
    sections.extend(
        [
            metrics,
            ft.Divider(),
            ft.Row(
                [agent_chart, model_chart],
                expand=True,
                spacing=24,
                vertical_alignment=ft.CrossAxisAlignment.START,
                wrap=True,
            ),
            trend,
            table,
        ],
    )

    if summary.total_calls == 0:
        sections.append(
            ft.Text(
                "Jalankan agent-builder run … untuk mengisi data biaya.",
                size=12,
                italic=True,
                color=tokens.on_surface,
            ),
        )

    return ft.Container(
        expand=True,
        padding=16,
        content=ft.Column(sections, expand=True, spacing=16, scroll=ft.ScrollMode.AUTO),
    )
