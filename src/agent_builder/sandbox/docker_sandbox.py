"""Layer 2 sandbox: Docker container (Fase 4 — stub)."""

from __future__ import annotations

from pathlib import Path

from agent_builder.sandbox.base import Sandbox, SandboxResult
from agent_builder.sandbox.exceptions import SandboxError


class DockerSandbox(Sandbox):
    """Docker-based sandbox (not implemented in Fase 1)."""

    async def run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> SandboxResult:
        raise SandboxError("DockerSandbox is not implemented yet (planned for Fase 4)")
