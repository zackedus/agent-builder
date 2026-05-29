"""Unit tests for Docker sandbox (mocked CLI)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_builder.sandbox.docker_sandbox import DockerSandbox
from agent_builder.sandbox.docker_util import container_workdir, host_mount_path
from agent_builder.sandbox.exceptions import SandboxError
from agent_builder.sandbox.factory import create_project_sandbox
from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "main.py").write_text("print('ok')\n", encoding="utf-8")
    return ws


def test_container_workdir_maps_relative_path(workspace: Path) -> None:
    sub = workspace / "pkg"
    sub.mkdir()
    assert container_workdir(workspace, sub) == "/workspace/pkg"


def test_host_mount_path_is_absolute(workspace: Path) -> None:
    mount = host_mount_path(workspace)
    assert Path(mount).is_absolute()


@pytest.mark.asyncio
async def test_docker_sandbox_run_command_invokes_docker(workspace: Path) -> None:
    sandbox = DockerSandbox(workspace, image="agent-builder-sandbox:3.11", timeout=30.0)

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"hello\n", b""))
    mock_proc.returncode = 0
    mock_proc.kill = AsyncMock()
    mock_proc.wait = AsyncMock()

    with patch(
        "agent_builder.sandbox.docker_sandbox.asyncio.create_subprocess_exec",
        AsyncMock(return_value=mock_proc),
    ) as mock_exec:
        result = await sandbox.run_command(["python", "-c", "print(1)"], cwd=workspace)

    assert result.success
    assert "hello" in result.stdout
    args = mock_exec.call_args[0]
    assert args[0] == "docker"
    assert "--network=none" in args
    assert "--rm" in args


def test_create_project_sandbox_falls_back_without_docker(
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agent_builder.sandbox.factory.is_docker_available",
        lambda: False,
    )
    sb = create_project_sandbox(workspace, layer="auto")
    assert isinstance(sb, SubprocessSandbox)


def test_create_project_sandbox_raises_when_docker_required(
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agent_builder.sandbox.factory.is_docker_available",
        lambda: False,
    )
    with pytest.raises(SandboxError, match="not available"):
        create_project_sandbox(workspace, layer="docker")


def test_create_project_sandbox_uses_docker_when_available(
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agent_builder.sandbox.factory.is_docker_available",
        lambda: True,
    )
    monkeypatch.setattr(
        "agent_builder.sandbox.factory.ensure_sandbox_image",
        lambda **_: "agent-builder-sandbox:3.11",
    )
    sb = create_project_sandbox(workspace, layer="auto")
    assert isinstance(sb, DockerSandbox)
