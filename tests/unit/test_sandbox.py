import sys
from pathlib import Path

import pytest

from agent_builder.sandbox.exceptions import (
    SandboxExecutionError,
    SandboxPathError,
    SandboxSecurityError,
)
from agent_builder.sandbox.static_check import StaticSecurityChecker
from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "project").mkdir()
    return ws


@pytest.fixture
def sandbox(workspace: Path) -> SubprocessSandbox:
    return SubprocessSandbox(workspace, timeout=30.0)


@pytest.mark.asyncio
async def test_run_python_hello(sandbox: SubprocessSandbox, workspace: Path) -> None:
    result = await sandbox.run_python("print('sandbox-ok')", cwd=workspace / "project")
    assert result.success
    assert "sandbox-ok" in result.stdout


@pytest.mark.asyncio
async def test_run_python_file(sandbox: SubprocessSandbox, workspace: Path) -> None:
    script = workspace / "project" / "hello.py"
    script.write_text("print('from-file')\n", encoding="utf-8")
    result = await sandbox.run_python_file(script)
    assert result.success
    assert "from-file" in result.stdout


@pytest.mark.asyncio
async def test_cwd_must_be_inside_workspace(sandbox: SubprocessSandbox, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(SandboxPathError):
        await sandbox.run_python("print(1)", cwd=outside)


def test_static_check_blocks_os_system() -> None:
    checker = StaticSecurityChecker()
    result = checker.check("import os\nos.system('rm -rf /')")
    assert not result.passed
    assert any("os.system" in issue for issue in result.issues)


def test_static_check_blocks_eval() -> None:
    checker = StaticSecurityChecker()
    result = checker.check("eval('1+1')")
    assert not result.passed


def test_static_check_allows_safe_code() -> None:
    checker = StaticSecurityChecker()
    result = checker.check("def add(a, b):\n    return a + b\n")
    assert result.passed


@pytest.mark.asyncio
async def test_run_python_blocks_dangerous_code(
    sandbox: SubprocessSandbox,
    workspace: Path,
) -> None:
    result = await sandbox.run_python(
        "import os\nos.system('echo pwned')",
        cwd=workspace / "project",
    )
    assert result.blocked
    assert result.block_reason is not None
    assert "os.system" in result.block_reason


def test_static_check_or_raise() -> None:
    checker = StaticSecurityChecker()
    with pytest.raises(SandboxSecurityError):
        checker.check_or_raise("exec('bad')")


@pytest.mark.asyncio
async def test_run_command_timeout(sandbox: SubprocessSandbox, workspace: Path) -> None:
    if sys.platform == "win32":
        hang_cmd = [
            sys.executable,
            "-c",
            "import time; time.sleep(60)",
        ]
    else:
        hang_cmd = ["sleep", "60"]

    short = SubprocessSandbox(workspace, timeout=0.3)
    with pytest.raises(SandboxExecutionError):
        await short.run_command(hang_cmd, cwd=workspace / "project")


@pytest.mark.asyncio
async def test_security_escape_blocked_before_execution(
    sandbox: SubprocessSandbox,
    workspace: Path,
) -> None:
    """Dangerous code must not run — blocked by static check, no shell output."""
    result = await sandbox.run_python(
        "import subprocess\nsubprocess.run(['echo', 'escaped'], shell=True)",
        cwd=workspace / "project",
    )
    assert result.blocked
    assert "escaped" not in result.stdout
