"""Abstract sandbox interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SandboxResult:
    """Result of a sandboxed command execution."""

    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    command: list[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.blocked


class Sandbox(ABC):
    """Execute commands in an isolated environment."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    @property
    def python_bin(self) -> str:
        """Python executable used inside ``run_command`` for module invocations."""
        import sys

        return sys.executable

    def ensure_cwd(self, cwd: Path | None) -> Path:
        """Resolve *cwd* and verify it stays inside ``workspace_root``."""
        target = (cwd or self.workspace_root).resolve()
        root = self.workspace_root
        try:
            target.relative_to(root)
        except ValueError as exc:
            from agent_builder.sandbox.exceptions import SandboxPathError

            raise SandboxPathError(f"cwd must be inside workspace: {target}") from exc
        return target

    @abstractmethod
    async def run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> SandboxResult:
        """Run a shell command."""

    async def run_python(
        self,
        code: str,
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> SandboxResult:
        """Run Python source code in the sandbox."""
        import sys

        return await self.run_command(
            [sys.executable, "-c", code],
            cwd=cwd,
            timeout=timeout,
        )

    async def run_python_file(
        self,
        script_path: Path,
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> SandboxResult:
        """Run a Python script file inside the workspace."""
        import sys

        resolved = script_path.resolve()
        self.ensure_cwd(resolved.parent)
        return await self.run_command(
            [sys.executable, str(resolved)],
            cwd=cwd or resolved.parent,
            timeout=timeout,
        )
