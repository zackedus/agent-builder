"""Rich console output helpers for the CLI."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import Plan, SessionState
from agent_builder.core.workspace import Workspace
from agent_builder.llm.cost_tracker import estimate_cost
from agent_builder.validation.project_output import BuildMetricsSummary


def print_session_summary(
    console: Console,
    session: SessionState,
    workspace: Workspace,
    *,
    title: str = "Session",
) -> None:
    """Render session overview as a Rich table."""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Field", style="dim")
    table.add_column("Value")

    state_style = "green" if not session.is_terminal() else "yellow"
    table.add_row("Session ID", session.session_id)
    table.add_row("State", f"[{state_style}]{session.current_state}[/{state_style}]")
    table.add_row("Current task", session.current_task or "—")
    table.add_row(
        "Prompt",
        session.user_prompt[:120] + ("…" if len(session.user_prompt) > 120 else ""),
    )
    table.add_row("Completed tasks", ", ".join(session.completed_tasks) or "—")
    table.add_row("Failed tasks", ", ".join(session.failed_tasks) or "—")
    table.add_row(
        "Retries",
        ", ".join(f"{k}={v}" for k, v in session.retry_count.items()) or "—",
    )
    table.add_row("LLM calls", str(session.metrics.total_llm_calls))
    table.add_row("Cost (USD)", f"${session.metrics.total_cost_usd:.4f}")
    table.add_row("Workspace", str(workspace.root))

    console.print(table)


def print_recent_events(
    console: Console,
    events: list[Event],
    *,
    limit: int = 8,
) -> None:
    """Show the most recent events from ``events.jsonl``."""
    if not events:
        console.print("[dim]No events logged yet.[/dim]")
        return

    table = Table(title=f"Recent events (last {min(limit, len(events))})", show_lines=False)
    table.add_column("Time", style="dim", max_width=22)
    table.add_column("Type", style="cyan")
    table.add_column("Detail")

    for event in events[-limit:]:
        detail = _format_event_detail(event)
        ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(ts, event.type.value, detail)

    console.print(table)


def print_cost_summary(console: Console, events: list[Event]) -> None:
    """Summarize LLM cost from event log."""
    total = 0.0
    calls = 0
    for event in events:
        if event.type != EventType.LLM_CALL:
            continue
        calls += 1
        total += estimate_cost(
            str(event.payload.get("model", "ollama")),
            int(event.payload.get("input_tokens", 0)),
            int(event.payload.get("output_tokens", 0)),
        )
    if calls == 0:
        return
    console.print(Panel(f"LLM calls: {calls}  |  Estimated cost: ${total:.4f}", title="Cost"))


def _format_event_detail(event: Event) -> str:
    if event.type == EventType.STATE_CHANGED:
        return (
            f"{event.payload.get('from', '?')} → {event.payload.get('to', '?')} "
            f"({event.payload.get('event', '')})"
        )
    if event.type == EventType.LLM_CALL:
        return (
            f"{event.payload.get('agent', '?')} / {event.payload.get('model', '?')} "
            f"in={event.payload.get('input_tokens', 0)} out={event.payload.get('output_tokens', 0)}"
        )
    if event.type in (EventType.TASK_STARTED, EventType.TASK_COMPLETED, EventType.TASK_FAILED):
        return str(event.payload.get("task_id", event.payload))
    return str(event.payload)[:80] if event.payload else "—"


def print_plan_summary(console: Console, plan: Plan) -> None:
    """Render planner output overview."""
    table = Table(title="Plan", show_header=True, header_style="bold green")
    table.add_column("Field", style="dim")
    table.add_column("Value")
    table.add_row("Project", plan.project_name)
    table.add_row("Complexity", plan.estimated_complexity)
    table.add_row("Tasks", str(len(plan.tasks)))
    table.add_row("Risks", "; ".join(plan.risks[:3]) if plan.risks else "—")
    desc = plan.description
    if len(desc) > 200:
        desc = desc[:200] + "…"
    table.add_row("Description", desc)
    console.print(table)

    task_table = Table(title="Tasks (first 10)", show_lines=False)
    task_table.add_column("ID", style="cyan")
    task_table.add_column("Type")
    task_table.add_column("Title")
    for task in plan.tasks[:10]:
        task_table.add_row(task.id, task.type, task.title[:60])
    if len(plan.tasks) > 10:
        task_table.add_row("…", "", f"+{len(plan.tasks) - 10} more")
    console.print(task_table)


def print_build_metrics(console: Console, summary: BuildMetricsSummary) -> None:
    """Show build duration and LLM usage after a completed pipeline."""
    console.print(
        Panel(
            f"LLM calls: {summary.total_llm_calls}  |  "
            f"Tokens in/out: {summary.input_tokens}/{summary.output_tokens}  |  "
            f"Cost: ${summary.total_cost_usd:.4f}  |  "
            f"Duration: {summary.elapsed_seconds}s",
            title="Build metrics",
        )
    )


def workspace_has_session(workspace: Workspace) -> bool:
    return workspace.state_path.is_file()
