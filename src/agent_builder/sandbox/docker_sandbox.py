"""Layer 2 sandbox: isolated execution via Docker."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from agent_builder.sandbox.base import Sandbox, SandboxResult
from agent_builder.sandbox.docker_util import (
    _DEFAULT_CPUS,
    _DEFAULT_MEMORY,
    CONTAINER_WORKDIR,
    SANDBOX_IMAGE,
    container_workdir,
    host_mount_path,
)
from agent_builder.sandbox.exceptions import SandboxExecutionError


class DockerSandbox(Sandbox):
    """Run commands in a short-lived Docker container with network isolation."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        image: str = SANDBOX_IMAGE,
        timeout: float = 300.0,
        cpus: str = _DEFAULT_CPUS,
        memory: str = _DEFAULT_MEMORY,
        network: str = "none",
        user: str = "1000:1000",
    ) -> None:
        super().__init__(workspace_root)
        self.image = image
        self.default_timeout = timeout
        self.cpus = cpus
        self.memory = memory
        self.network = network
        self.user = user

    @property
    def python_bin(self) -> str:
        return "python"

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
        timeout_s = timeout if timeout is not None else self.default_timeout
        container_cwd = container_workdir(self.workspace_root, safe_cwd)
        mount = host_mount_path(self.workspace_root)

        docker_cmd = [
            "docker",
            "run",
            "--rm",
            f"--network={self.network}",
            f"--cpus={self.cpus}",
            f"--memory={self.memory}",
            f"--user={self.user}",
            "-v",
            f"{mount}:{CONTAINER_WORKDIR}:rw",
            "-w",
            container_cwd,
            self.image,
            *command,
        ]

        start = time.perf_counter()
        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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
            raise SandboxExecutionError(
                f"Docker command timed out after {timeout_s}s: {' '.join(command)}"
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
