"""Run orchestrator jobs from the dashboard (in-process asyncio)."""

from __future__ import annotations

from agent_builder.config import Settings, get_settings
from agent_builder.core.event_bus import EventBus
from agent_builder.core.logging_setup import configure_logging
from agent_builder.core.orchestrator import Orchestrator
from agent_builder.core.state import OrchestratorState, SessionState
from agent_builder.core.workspace import Workspace


def _settings_with_budget(budget_usd: float | None) -> Settings:
    settings = get_settings()
    if budget_usd is not None and budget_usd > 0:
        return settings.model_copy(update={"budget_usd": budget_usd})
    return settings


async def start_new_build(
    workspace: Workspace,
    prompt: str,
    *,
    budget_usd: float | None = None,
    event_bus: EventBus | None = None,
) -> tuple[bool, str]:
    """Start a new build session (same as ``agent-builder run``)."""
    text = prompt.strip()
    if not text:
        return False, "Prompt tidak boleh kosong."

    settings = _settings_with_budget(budget_usd)
    if not settings.anthropic_configured():
        return False, "ANTHROPIC_API_KEY belum diset. Isi .env lalu restart dashboard."

    configure_logging(workspace, level=settings.log_level)
    orch = Orchestrator(workspace, settings=settings, event_bus=event_bus)
    orch.start(text)
    session = await orch.run_build_pipeline(auto_approve=True)
    return _finalize_message(session, workspace)


async def resume_build(
    workspace: Workspace,
    *,
    event_bus: EventBus | None = None,
) -> tuple[bool, str]:
    """Resume non-terminal session (same as ``agent-builder resume``)."""
    session = workspace.load_session()
    if session is None:
        return False, "Tidak ada session. Mulai build baru dulu."

    if session.is_terminal():
        return (
            False,
            f"Session sudah selesai ({session.current_state}). Mulai build baru.",
        )

    settings = get_settings()
    configure_logging(workspace, level=settings.log_level)
    orch = Orchestrator(workspace, settings=settings, event_bus=event_bus)
    orch.session = session
    session = await orch.run_build_pipeline(auto_approve=True)
    return _finalize_message(session, workspace)


def _finalize_message(session: SessionState | None, workspace: Workspace) -> tuple[bool, str]:
    if session is None:
        return False, "Build gagal (session hilang)."

    state = session.current_state
    if state == OrchestratorState.DONE:
        return True, f"Build selesai. Output: {workspace.project_dir}"
    if state == OrchestratorState.FAILED:
        return False, "Build gagal. Lihat tab Replay / activity feed."
    return True, f"Build berhenti di {state}. Klik Lanjutkan untuk melanjutkan."
