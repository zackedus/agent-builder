"""Create the best available sandbox for a project directory."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from agent_builder.config import Settings, get_settings
from agent_builder.sandbox.base import Sandbox
from agent_builder.sandbox.docker_sandbox import DockerSandbox
from agent_builder.sandbox.docker_util import ensure_sandbox_image, is_docker_available
from agent_builder.sandbox.exceptions import SandboxError
from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox

logger = logging.getLogger(__name__)

SandboxLayer = Literal["subprocess", "docker", "auto"]


def create_project_sandbox(
    project_dir: Path,
    *,
    settings: Settings | None = None,
    timeout: float = 60.0,
    layer: SandboxLayer | None = None,
) -> Sandbox:
    """Return Layer 2 (Docker) when configured and available, else Layer 1."""
    cfg = settings or get_settings()
    chosen = layer or cfg.sandbox_layer

    if chosen == "subprocess":
        return SubprocessSandbox(project_dir, timeout=timeout)

    if chosen in ("docker", "auto"):
        if is_docker_available():
            try:
                ensure_sandbox_image()
                return DockerSandbox(project_dir, timeout=timeout)
            except SandboxError as exc:
                if chosen == "docker":
                    raise
                logger.info("Docker sandbox unavailable, using subprocess: %s", exc)
        elif chosen == "docker":
            raise SandboxError("Docker sandbox requested but Docker is not available")

    return SubprocessSandbox(project_dir, timeout=timeout)
