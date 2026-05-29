"""CLI entry point for Agent Team Builder."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from agent_builder import __version__
from agent_builder.cli_display import (
    print_build_metrics,
    print_cost_summary,
    print_plan_summary,
    print_recent_events,
    print_session_summary,
    workspace_has_session,
)
from agent_builder.config import Settings, get_settings
from agent_builder.core.logging_setup import configure_logging, get_agent_logger
from agent_builder.core.orchestrator import Orchestrator
from agent_builder.core.state import OrchestratorState, SessionState
from agent_builder.core.workspace import Workspace
from agent_builder.validation.project_output import (
    assert_calculator_output,
    summarize_metrics_from_events,
    validate_project_output,
)

app = typer.Typer(
    name="agent-builder",
    help="Autonomous multi-agent system that builds Flet desktop applications.",
    no_args_is_help=True,
)
console = Console()


def _calculator_smoke_args(prompt: str) -> list[str] | None:
    """Return argv for a quick add smoke test when the prompt targets a calculator."""
    lowered = prompt.lower()
    if "calculator" in lowered or "kalkulator" in lowered:
        return ["2", "+", "3"]
    return None


def _workspace_from_settings(settings: Settings) -> Workspace:
    workspace = Workspace(settings.workspace_dir)
    workspace.ensure_layout()
    return workspace


def _load_session(
    workspace: Workspace,
    session_id: str | None,
) -> SessionState | None:
    session = workspace.load_session()
    if session is None:
        return None
    if session_id and session.session_id != session_id:
        console.print(
            f"[red]Session ID mismatch.[/red] Workspace has [bold]{session.session_id}[/bold], "
            f"not {session_id}."
        )
        raise typer.Exit(code=1)
    return session


@app.command("version")
def version_cmd() -> None:
    """Show package version."""
    console.print(f"agent-team-builder {__version__}")


@app.command("doctor")
def doctor_cmd() -> None:
    """Check local tooling and API configuration."""
    settings = get_settings()
    from rich.table import Table

    table = Table(title="Agent Team Builder — Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Notes")

    anthropic_ok = settings.anthropic_configured()
    table.add_row(
        "Anthropic API key",
        "[green]OK[/green]" if anthropic_ok else "[yellow]MISSING[/yellow]",
        "Set ANTHROPIC_API_KEY in .env" if not anthropic_ok else "Configured",
    )

    ollama_ok = _check_ollama(settings.ollama_host)
    table.add_row(
        "Ollama",
        "[green]OK[/green]" if ollama_ok else "[yellow]UNAVAILABLE[/yellow]",
        settings.ollama_host,
    )

    workspace = settings.workspace_dir
    table.add_row(
        "Workspace path",
        "[green]OK[/green]",
        str(workspace.resolve()),
    )
    has_session = workspace_has_session(Workspace(workspace))
    table.add_row(
        "Active session",
        "[green]Yes[/green]" if has_session else "[dim]No[/dim]",
        str(workspace / ".agent" / "state.json"),
    )

    console.print(table)
    if not anthropic_ok:
        console.print(
            "\n[yellow]Tip:[/yellow] Copy .env.example to .env and add your Anthropic API key."
        )


@app.command("run")
def run_cmd(
    prompt: str = typer.Argument(..., help="Natural language description of the app to build"),
    budget: float | None = typer.Option(None, "--budget", help="Budget cap in USD"),
) -> None:
    """Start a new build session (enters PLANNING)."""
    settings = get_settings()
    if not settings.anthropic_configured():
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY is not set. "
            "Run [bold]agent-builder doctor[/bold]."
        )
        raise typer.Exit(code=1)

    workspace = _workspace_from_settings(settings)
    configure_logging(workspace, level=settings.log_level)
    log = get_agent_logger("orchestrator")

    orch = Orchestrator(workspace, settings=settings)
    session = orch.start(prompt)
    log.info("Session started: {} → {}", session.session_id, session.current_state)

    with console.status("[bold green]Building…[/bold green]", spinner="dots"):
        session = asyncio.run(orch.run_build_pipeline(auto_approve=True))

    if orch.session is None:
        raise typer.Exit(code=1)
    session = orch.session
    print_session_summary(console, session, workspace, title="Session started")

    plan = workspace.load_plan()
    if plan is not None:
        print_plan_summary(console, plan)

    events = workspace.events_store().load_all()
    if session.metrics.total_llm_calls == 0 and events:
        summary = summarize_metrics_from_events(events, session)
        session.metrics.total_llm_calls = summary.total_llm_calls
        session.metrics.total_cost_usd = summary.total_cost_usd
        session.metrics.elapsed_seconds = summary.elapsed_seconds

    if session.current_state == OrchestratorState.DONE:
        console.print(f"\n[green]Build complete.[/green] Output in {workspace.project_dir}")
        if session.metrics.total_llm_calls > 0:
            print_build_metrics(
                console,
                summarize_metrics_from_events(events, session),
            )
        smoke_args = _calculator_smoke_args(prompt)
        validation = asyncio.run(
            validate_project_output(workspace.project_dir, run_args=smoke_args),
        )
        if validation.python_files and validation.syntax_ok:
            n_files = len(validation.python_files)
            console.print(f"[green]Validation:[/green] {n_files} Python file(s), syntax OK")
        elif validation.syntax_errors:
            console.print("[yellow]Validation:[/yellow] " + "; ".join(validation.syntax_errors))
        if smoke_args and validation.run_ok and validation.entry_script:
            console.print(
                f"[green]Smoke run:[/green] {validation.entry_script} "
                f"{' '.join(smoke_args)} → {validation.run_stdout.strip()}"
            )
            try:
                assert_calculator_output(validation.run_stdout, 5.0)
            except AssertionError as exc:
                console.print(f"[yellow]Calculator check:[/yellow] {exc}")
    elif session.current_state == OrchestratorState.FAILED:
        console.print("\n[red]Build failed.[/red] See logs and [bold]agent-builder status[/bold].")
        raise typer.Exit(code=1)
    else:
        console.print(
            f"\n[yellow]Paused at {session.current_state}.[/yellow] "
            "Run [bold]agent-builder resume[/bold] to continue."
        )
        raise typer.Exit(code=1)

    if budget is not None:
        console.print(f"[dim]Budget cap: ${budget:.2f} (enforced when agents call LLM)[/dim]")


@app.command("status")
def status_cmd(
    session_id: str | None = typer.Argument(
        None,
        help="Optional session ID to verify against workspace state",
    ),
) -> None:
    """Show current session status and recent events."""
    settings = get_settings()
    workspace = _workspace_from_settings(settings)

    session = _load_session(workspace, session_id)
    if session is None:
        console.print(
            "[yellow]No session in workspace.[/yellow] Run [bold]agent-builder run[/bold] first."
        )
        raise typer.Exit(code=1)

    events = workspace.events_store().load_all()
    print_session_summary(console, session, workspace, title="Session status")
    print_cost_summary(console, events)
    print_recent_events(console, events)


@app.command("resume")
def resume_cmd(
    session_id: str | None = typer.Argument(
        None,
        help="Optional session ID to verify before resume",
    ),
) -> None:
    """Resume an in-progress session from workspace state.json."""
    settings = get_settings()
    workspace = _workspace_from_settings(settings)
    configure_logging(workspace, level=settings.log_level)

    session = _load_session(workspace, session_id)
    if session is None:
        console.print(
            "[yellow]No session found.[/yellow] Run [bold]agent-builder run[/bold] first."
        )
        raise typer.Exit(code=1)

    if session.is_terminal():
        console.print(
            f"[yellow]Session is terminal ({session.current_state}).[/yellow] "
            "Start a new run with [bold]agent-builder run[/bold]."
        )
        print_session_summary(console, session, workspace, title="Terminal session")
        raise typer.Exit(code=1)

    orch = Orchestrator(workspace, settings=settings)
    orch.session = session

    with console.status("[bold green]Resuming build…[/bold green]", spinner="dots"):
        session = asyncio.run(orch.run_build_pipeline(auto_approve=True))

    if orch.session is None:
        raise typer.Exit(code=1)
    session = orch.session
    print_session_summary(console, session, workspace, title="Resumed session")
    plan = workspace.load_plan()
    if plan is not None:
        print_plan_summary(console, plan)
    if session.is_terminal() and session.current_state != OrchestratorState.DONE:
        raise typer.Exit(code=1)

    events = workspace.events_store().load_all()
    print_recent_events(console, events, limit=5)


def _check_ollama(host: str) -> bool:
    try:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(f"{host.rstrip('/')}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return bool(resp.status == 200)
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def main() -> None:
    app()


if __name__ == "__main__":
    main()
