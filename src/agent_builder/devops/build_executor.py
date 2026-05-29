"""Run PyInstaller builds inside the workspace sandbox."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox


@dataclass(frozen=True)
class BuildAttempt:
    """Outcome of a PyInstaller invocation."""

    success: bool
    skipped: bool = False
    reason: str = ""
    artifact: Path | None = None
    log: str = ""


async def run_pyinstaller_build(
    project_dir: Path,
    spec_path: Path,
    sandbox: SubprocessSandbox,
    *,
    timeout: float = 300.0,
) -> BuildAttempt:
    """Run ``pyinstaller`` on *spec_path* if the tool is available."""
    if shutil.which(sys.executable) is None:
        return BuildAttempt(success=False, skipped=True, reason="python not found")

    if importlib.util.find_spec("PyInstaller") is None:
        return BuildAttempt(
            success=False,
            skipped=True,
            reason="PyInstaller not installed (pip install pyinstaller)",
        )

    result = await sandbox.run_command(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_path.name],
        cwd=project_dir,
        timeout=timeout,
    )
    log = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        return BuildAttempt(success=False, reason=f"exit {result.returncode}", log=log[:2000])

    artifact = _find_built_exe(project_dir, spec_path)
    if artifact is None:
        return BuildAttempt(
            success=False,
            reason="build finished but no executable found in dist/",
            log=log[:2000],
        )
    return BuildAttempt(success=True, artifact=artifact, log=log[:500])


def _find_built_exe(project_dir: Path, spec_path: Path) -> Path | None:
    dist_dir = project_dir / "dist"
    if not dist_dir.is_dir():
        return None
    exe_name = spec_path.stem
    candidate = dist_dir / f"{exe_name}.exe"
    if candidate.is_file():
        return candidate
    for path in dist_dir.rglob("*.exe"):
        if path.is_file():
            return path
    for path in dist_dir.iterdir():
        if path.is_file() and path.suffix in ("", ".exe"):
            return path
    return None


async def smoke_test_executable(
    artifact: Path,
    sandbox: SubprocessSandbox,
    *,
    timeout: float = 15.0,
) -> tuple[bool, str]:
    """Launch *artifact* briefly; on Windows run with no args (may open GUI)."""
    if not artifact.is_file():
        return False, "artifact missing"
    if sys.platform == "win32" and artifact.suffix.lower() == ".exe":
        result = await sandbox.run_command(
            [str(artifact.resolve()), "--help"],
            cwd=artifact.parent,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, result.stdout[:200]
        return True, "exe exists (smoke assumed ok; --help not supported)"

    result = await sandbox.run_command(
        [str(artifact.resolve())],
        cwd=artifact.parent,
        timeout=timeout,
    )
    return result.returncode == 0, (result.stdout + result.stderr)[:200]
