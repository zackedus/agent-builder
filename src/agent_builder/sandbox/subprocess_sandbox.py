"""Layer 1 sandbox: subprocess with cwd lock, timeout, env whitelist, static checks."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

from agent_builder.sandbox.base import Sandbox, SandboxResult
from agent_builder.sandbox.exceptions import SandboxExecutionError
from agent_builder.sandbox.static_check import StaticSecurityChecker

DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MEMORY_BYTES = 512 * 1024 * 1024  # 512 MiB

# Minimal environment for child processes.
DEFAULT_ENV_KEYS: frozenset[str] = frozenset(
    {
        "PATH",
        "SYSTEMROOT",
        "SystemRoot",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "PYTHONIOENCODING",
        "PYTHONUTF8",
        "LANG",
        "LC_ALL",
    }
)


def _build_env(whitelist: frozenset[str], extra: dict[str, str] | None) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in whitelist:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    if extra:
        env.update(extra)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _resource_limit_preexec(memory_bytes: int) -> Callable[[], None] | None:
    """Return preexec_fn for memory limits on Unix (no-op on Windows)."""
    if sys.platform == "win32":
        return None

    def _set_limits() -> None:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (DEFAULT_TIMEOUT_S, DEFAULT_TIMEOUT_S))
        except OSError:
            pass

    return _set_limits


class SubprocessSandbox(Sandbox):
    """Execute commands in a subprocess confined to the workspace."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        timeout: float = DEFAULT_TIMEOUT_S,
        memory_bytes: int = DEFAULT_MEMORY_BYTES,
        env_whitelist: frozenset[str] | None = None,
        extra_env: dict[str, str] | None = None,
        checker: StaticSecurityChecker | None = None,
        check_python: bool = True,
    ) -> None:
        super().__init__(workspace_root)
        self.default_timeout = timeout
        self.memory_bytes = memory_bytes
        self.env_whitelist = env_whitelist or DEFAULT_ENV_KEYS
        self.extra_env = extra_env
        self.checker = checker or StaticSecurityChecker()
        self.check_python = check_python

    async def run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> SandboxResult:
        if not command:
            raise SandboxExecutionError("Command must not be empty")

        safe_cwd = self.ensure_cwd(cwd)
        env = _build_env(self.env_whitelist, self.extra_env)
        timeout_s = timeout if timeout is not None else self.default_timeout
        preexec = _resource_limit_preexec(self.memory_bytes)

        start = time.perf_counter()
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(safe_cwd),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=preexec,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_s,
            )
            returncode = proc.returncode if proc.returncode is not None else -1
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            duration = time.perf_counter() - start
            raise SandboxExecutionError(
                f"Command timed out after {timeout_s}s: {' '.join(command)}"
            ) from exc
        finally:
            duration = time.perf_counter() - start

        return SandboxResult(
            returncode=returncode,
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            duration_s=duration,
            command=list(command),
        )

    async def run_python(
        self,
        code: str,
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> SandboxResult:
        if self.check_python:
            check = self.checker.check(code)
            if not check.passed:
                return SandboxResult(
                    returncode=-1,
                    stdout="",
                    stderr="",
                    duration_s=0.0,
                    command=[sys.executable, "-c", "<blocked>"],
                    blocked=True,
                    block_reason="; ".join(check.issues),
                )
        return await super().run_python(code, cwd=cwd, timeout=timeout)

    async def run_python_file(
        self,
        script_path: Path,
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> SandboxResult:
        resolved = script_path.resolve()
        self.ensure_cwd(resolved.parent)
        if self.check_python and resolved.is_file():
            source = resolved.read_text(encoding="utf-8")
            check = self.checker.check(source, filename=str(resolved))
            if not check.passed:
                return SandboxResult(
                    returncode=-1,
                    stdout="",
                    stderr="",
                    duration_s=0.0,
                    command=[sys.executable, str(resolved)],
                    blocked=True,
                    block_reason="; ".join(check.issues),
                )
        return await super().run_python_file(resolved, cwd=cwd, timeout=timeout)
