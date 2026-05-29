"""Run ruff and mypy against the generated project."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from agent_builder.agents.test_models import CheckStatus
from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox


def _tool_unavailable(output: str) -> bool:
    lowered = output.lower()
    return "no module named" in lowered or "not found" in lowered or "not recognized" in lowered


@dataclass(frozen=True)
class ToolRunResult:
    status: CheckStatus
    output: str


async def run_ruff(project_dir: Path, sandbox: SubprocessSandbox) -> ToolRunResult:
    """Run ``ruff check`` on *project_dir*."""
    result = await sandbox.run_command(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=project_dir,
        timeout=120.0,
    )
    if result.blocked:
        return ToolRunResult("skipped", result.block_reason or "blocked")
    combined = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode == 0:
        return ToolRunResult("passed", combined or "OK")
    if _tool_unavailable(combined):
        return ToolRunResult("skipped", combined)
    return ToolRunResult("failed", combined or f"exit {result.returncode}")


async def run_mypy(project_dir: Path, sandbox: SubprocessSandbox) -> ToolRunResult:
    """Run ``mypy`` on Python files under *project_dir*."""
    py_files = sorted(project_dir.rglob("*.py"))
    if not py_files:
        return ToolRunResult("skipped", "no Python files")
    targets = [str(p.relative_to(project_dir)) for p in py_files[:50]]
    result = await sandbox.run_command(
        [sys.executable, "-m", "mypy", *targets],
        cwd=project_dir,
        timeout=180.0,
    )
    if result.blocked:
        return ToolRunResult("skipped", result.block_reason or "blocked")
    combined = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode == 0:
        return ToolRunResult("passed", combined or "OK")
    if _tool_unavailable(combined):
        return ToolRunResult("skipped", combined)
    return ToolRunResult("failed", combined or f"exit {result.returncode}")
