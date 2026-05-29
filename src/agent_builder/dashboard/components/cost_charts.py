"""Cost breakdown UI widgets (native Flet bars + canvas trend)."""

from __future__ import annotations

from typing import Any

from agent_builder.dashboard.cost.aggregates import (
    AgentCostRow,
    CostSummary,
    ModelCostRow,
    TokenTableRow,
    TrendPoint,
)
from agent_builder.dashboard.theme import DashboardThemeTokens, agent_color
from agent_builder.llm.budget import BudgetLevel


def build_budget_banner(summary: CostSummary, tokens: DashboardThemeTokens) -> Any | None:
    import flet as ft

    if summary.budget_cap is None:
        return None

    level = summary.budget_level
    if level == BudgetLevel.OK:
        return None

    colors = {
        BudgetLevel.WARN_50: ("#FEF3C7", "#92400E"),
        BudgetLevel.WARN_80: ("#FEE2E2", "#991B1B"),
        BudgetLevel.EXCEEDED: ("#FECACA", "#7F1D1D"),
    }
    spent = summary.total_cost_usd
    cap = summary.budget_cap
    messages = {
        BudgetLevel.WARN_50: f"Budget 50% terpakai (${spent:.2f} / ${cap:.2f})",
        BudgetLevel.WARN_80: f"Budget 80% — planner dapat di-pause (${spent:.2f})",
        BudgetLevel.EXCEEDED: f"Budget habis — LLM call di-pause (${spent:.2f})",
    }
    bg, fg = colors.get(level, ("#FEE2E2", "#991B1B"))
    return ft.Container(
        bgcolor=bg,
        padding=12,
        border_radius=8,
        content=ft.Text(messages.get(level, "Budget alert"), color=fg, size=13),
    )


def build_cost_metrics_row(summary: CostSummary, tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    chips = [
        _metric_chip("Total", f"${summary.total_cost_usd:.4f}", tokens),
        _metric_chip("IDR", f"Rp {summary.total_cost_idr:,.0f}", tokens),
        _metric_chip("Burn rate", f"${summary.burn_rate_usd_per_min:.3f}/min", tokens),
    ]
    if summary.budget_cap is not None:
        remaining = summary.budget_remaining or 0.0
        chips.append(_metric_chip("Sisa budget", f"${remaining:.2f}", tokens))
    if summary.projected_total_usd is not None:
        chips.append(
            _metric_chip("Proyeksi", f"${summary.projected_total_usd:.2f}", tokens),
        )
    chips.append(_metric_chip("LLM calls", str(summary.total_calls), tokens))

    return ft.Row(chips, wrap=True, spacing=12)


def build_agent_bar_chart(
    rows: tuple[AgentCostRow, ...],
    total_cost: float,
    tokens: DashboardThemeTokens,
) -> Any:
    import flet as ft

    if not rows:
        return ft.Text("Belum ada data per agent.", italic=True, size=12)

    max_cost = max(row.cost_usd for row in rows) or 1.0
    bars: list[Any] = []
    for row in rows:
        pct = (row.cost_usd / total_cost * 100.0) if total_cost else 0.0
        width_frac = row.cost_usd / max_cost if max_cost else 0.0
        colors = agent_color(row.agent)
        bars.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(row.agent, width=80, size=12, weight=ft.FontWeight.W_600),
                            ft.Container(
                                expand=True,
                                height=18,
                                bgcolor=tokens.border,
                                border_radius=4,
                                content=ft.Container(
                                    width=max(4, int(280 * width_frac)),
                                    height=18,
                                    bgcolor=colors["fg"],
                                    border_radius=4,
                                ),
                            ),
                            ft.Text(
                                f"${row.cost_usd:.2f} ({pct:.0f}%)",
                                size=11,
                                width=100,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        f"{row.calls} calls · {row.primary_model}",
                        size=10,
                        color=tokens.on_surface,
                        opacity=0.7,
                    ),
                ],
                spacing=2,
            ),
        )
    return ft.Column(
        [ft.Text("Per agent", size=14, weight=ft.FontWeight.W_600), *bars],
        spacing=10,
    )


def build_model_breakdown(
    rows: tuple[ModelCostRow, ...],
    tokens: DashboardThemeTokens,
) -> Any:
    import flet as ft

    if not rows:
        return ft.Text("Belum ada data per model.", italic=True, size=12)

    items: list[Any] = []
    for row in rows:
        items.append(
            ft.Row(
                [
                    ft.Text(row.model, expand=True, size=12),
                    ft.Text(f"${row.cost_usd:.2f}", size=12, width=70),
                    ft.Text(f"{row.percent:.0f}%", size=11, width=40),
                    ft.Text(f"{row.calls} calls", size=10, color=tokens.on_surface),
                ],
            ),
        )
    return ft.Column(
        [ft.Text("Per model", size=14, weight=ft.FontWeight.W_600), *items],
        spacing=6,
    )


def build_cost_trend_chart(
    points: tuple[TrendPoint, ...],
    tokens: DashboardThemeTokens,
    *,
    projected_total: float | None = None,
) -> Any:
    import flet as ft
    import flet.canvas as cv

    if len(points) < 2:
        return ft.Column(
            [
                ft.Text("Trend biaya", size=14, weight=ft.FontWeight.W_600),
                ft.Text("Butuh ≥2 LLM call untuk trend.", size=12, italic=True),
            ],
        )

    width = 520.0
    height = 160.0
    max_x = max(p.minutes for p in points) or 1.0
    max_y = max(p.cumulative_usd for p in points) or 0.01
    if projected_total is not None:
        max_y = max(max_y, projected_total)

    def scale_x(m: float) -> float:
        return 20.0 + (m / max_x) * (width - 40.0)

    def scale_y(cost: float) -> float:
        return height - 20.0 - (cost / max_y) * (height - 40.0)

    stroke = ft.Paint(style=ft.PaintingStyle.STROKE, stroke_width=2, color=tokens.primary)
    axis = ft.Paint(style=ft.PaintingStyle.STROKE, stroke_width=1, color=tokens.border)

    shapes: list[Any] = [
        cv.Line(20, height - 20, width - 20, height - 20, paint=axis),
        cv.Line(20, 20, 20, height - 20, paint=axis),
    ]

    first = points[0]
    path_elements: list[Any] = [
        cv.Path.MoveTo(scale_x(first.minutes), scale_y(first.cumulative_usd)),
    ]
    for point in points[1:]:
        path_elements.append(
            cv.Path.LineTo(scale_x(point.minutes), scale_y(point.cumulative_usd)),
        )
    shapes.append(cv.Path(path_elements, paint=stroke))

    if projected_total is not None and points:
        last = points[-1]
        shapes.append(
            cv.Line(
                scale_x(last.minutes),
                scale_y(last.cumulative_usd),
                scale_x(max_x * 1.2),
                scale_y(projected_total),
                paint=ft.Paint(
                    style=ft.PaintingStyle.STROKE,
                    stroke_width=2,
                    color=tokens.on_surface,
                ),
            ),
        )

    return ft.Column(
        [
            ft.Text("Trend biaya (kumulatif)", size=14, weight=ft.FontWeight.W_600),
            cv.Canvas(shapes=shapes, width=width, height=height),
        ],
        spacing=8,
    )


def build_token_usage_table(rows: tuple[TokenTableRow, ...], tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    if not rows:
        return ft.Text("Tabel token kosong.", italic=True, size=12)

    header = ft.Row(
        [
            ft.Text("Agent", weight=ft.FontWeight.W_600, width=80),
            ft.Text("Model", weight=ft.FontWeight.W_600, width=120),
            ft.Text("In", weight=ft.FontWeight.W_600, width=70),
            ft.Text("Out", weight=ft.FontWeight.W_600, width=70),
            ft.Text("Calls", weight=ft.FontWeight.W_600, width=50),
            ft.Text("Cost", weight=ft.FontWeight.W_600, width=70),
        ],
        spacing=8,
    )
    body = [
        ft.Row(
            [
                ft.Text(row.agent, width=80, size=11),
                ft.Text(row.model, width=120, size=11),
                ft.Text(f"{row.input_tokens:,}", width=70, size=11),
                ft.Text(f"{row.output_tokens:,}", width=70, size=11),
                ft.Text(str(row.calls), width=50, size=11),
                ft.Text(f"${row.cost_usd:.4f}", width=70, size=11),
            ],
            spacing=8,
        )
        for row in rows
    ]

    return ft.ExpansionTile(
        title=ft.Text("Detail token", size=14, weight=ft.FontWeight.W_600),
        subtitle=ft.Text(f"{len(rows)} baris", size=11),
        controls=[
            ft.Container(
                padding=8,
                content=ft.Column(
                    [header, ft.Divider(height=1), *body], spacing=4, scroll=ft.ScrollMode.AUTO
                ),
            ),
        ],
    )


def _metric_chip(label: str, value: str, tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    return ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=tokens.surface_variant,
        border_radius=8,
        content=ft.Column(
            [
                ft.Text(label, size=10, color=tokens.on_surface, opacity=0.7),
                ft.Text(value, size=14, weight=ft.FontWeight.W_600),
            ],
            spacing=2,
        ),
    )
