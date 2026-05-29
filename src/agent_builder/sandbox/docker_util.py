"""Docker CLI helpers: availability check, image build, and path mapping."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agent_builder.sandbox.exceptions import SandboxError

SANDBOX_IMAGE = "agent-builder-sandbox:3.11"
_DEFAULT_CPUS = "2"
_DEFAULT_MEMORY = "2g"
CONTAINER_WORKDIR = "/workspace"


def dockerfile_path() -> Path:
    return Path(__file__).resolve().parent / "images" / "Dockerfile"


def is_docker_available() -> bool:
    """Return True when the Docker CLI responds to ``docker info``."""
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def image_exists(image: str = SANDBOX_IMAGE) -> bool:
    if not is_docker_available():
        return False
    proc = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
        timeout=15,
        check=False,
    )
    return proc.returncode == 0


def ensure_sandbox_image(*, image: str = SANDBOX_IMAGE, force: bool = False) -> str:
    """Build the sandbox image if missing."""
    if not is_docker_available():
        raise SandboxError("Docker is not installed or not running")

    if not force and image_exists(image):
        return image

    dockerfile = dockerfile_path()
    if not dockerfile.is_file():
        raise SandboxError(f"Sandbox Dockerfile not found: {dockerfile}")

    context = dockerfile.parent
    proc = subprocess.run(
        [
            "docker",
            "build",
            "-t",
            image,
            "-f",
            str(dockerfile),
            str(context),
        ],
        capture_output=True,
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).decode("utf-8", errors="replace")[:500]
        raise SandboxError(f"Failed to build sandbox image: {detail}")
    return image


def host_mount_path(workspace_root: Path) -> str:
    """Return a Docker-compatible bind-mount source path."""
    return str(workspace_root.resolve())


def container_workdir(workspace_root: Path, cwd: Path) -> str:
    """Map a host cwd under *workspace_root* to a path inside the container."""
    rel = cwd.resolve().relative_to(workspace_root.resolve())
    if rel.as_posix() == ".":
        return CONTAINER_WORKDIR
    return f"{CONTAINER_WORKDIR}/{rel.as_posix()}"
