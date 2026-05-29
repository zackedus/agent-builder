"""Environment checks (dashboard equivalent of ``agent-builder doctor``)."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen

from agent_builder.cli_display import workspace_has_session
from agent_builder.config import Settings, get_settings
from agent_builder.core.workspace import Workspace


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def _check_ollama(host: str) -> bool:
    try:
        req = Request(f"{host.rstrip('/')}/api/tags", method="GET")
        with urlopen(req, timeout=3) as resp:
            return bool(resp.status == 200)
    except (URLError, TimeoutError, OSError):
        return False


def run_doctor_checks(workspace: Workspace, settings: Settings | None = None) -> list[DoctorCheck]:
    """Return doctor rows for the control panel."""
    cfg = settings or get_settings()
    checks = [
        DoctorCheck(
            "Anthropic API key",
            cfg.anthropic_configured(),
            "Configured" if cfg.anthropic_configured() else "Set ANTHROPIC_API_KEY in .env",
        ),
        DoctorCheck(
            "Ollama",
            _check_ollama(cfg.ollama_host),
            cfg.ollama_host,
        ),
        DoctorCheck(
            "Workspace",
            workspace.root.is_dir(),
            str(workspace.root.resolve()),
        ),
        DoctorCheck(
            "Active session",
            workspace_has_session(workspace),
            str(workspace.agent_dir / "state.json"),
        ),
    ]
    return checks
