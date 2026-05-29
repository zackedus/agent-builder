"""Validate DevOps release artifacts and session cost budgets."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from agent_builder.core.workspace import Workspace
from agent_builder.devops.models import BuildReport
from agent_builder.devops.packager import platform_tag
from agent_builder.validation.project_output import BuildMetricsSummary


@dataclass
class ReleaseValidation:
    """Outcome of dist/ package and optional executable checks."""

    ok: bool = True
    errors: list[str] = field(default_factory=list)
    build_report: BuildReport | None = None
    package_path: Path | None = None
    artifact_path: Path | None = None


@dataclass
class LaunchValidation:
    ok: bool = True
    message: str = ""
    errors: list[str] = field(default_factory=list)


def load_build_report(workspace: Workspace) -> BuildReport | None:
    path = workspace.dist_dir / "BUILD_REPORT.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return BuildReport.model_validate(data)


def validate_release_artifacts(workspace: Workspace) -> ReleaseValidation:
    """Check ``dist/BUILD_REPORT.json`` and release zip exist."""
    outcome = ReleaseValidation()
    report = load_build_report(workspace)
    if report is None:
        outcome.ok = False
        outcome.errors.append("BUILD_REPORT.json missing under dist/")
        return outcome

    outcome.build_report = report
    if not report.is_acceptable():
        outcome.ok = False
        outcome.errors.append(f"build status not acceptable: {report.status}")

    if report.package_path:
        package = workspace.root / report.package_path.replace("/", "\\")
        if not package.is_file():
            outcome.ok = False
            outcome.errors.append(f"package missing: {report.package_path}")
        else:
            outcome.package_path = package
            try:
                with zipfile.ZipFile(package) as zf:
                    names = zf.namelist()
                if not any(n.startswith("project/") for n in names):
                    outcome.ok = False
                    outcome.errors.append("release zip has no project/ prefix entries")
            except zipfile.BadZipFile:
                outcome.ok = False
                outcome.errors.append(f"invalid zip: {package}")

    if report.artifact_path:
        artifact = workspace.project_dir / report.artifact_path.replace("/", "\\")
        if artifact.is_file():
            outcome.artifact_path = artifact
        else:
            outcome.ok = False
            outcome.errors.append(f"artifact missing: {report.artifact_path}")

    return outcome


def seed_mock_executable(workspace: Workspace, project_name: str = "expense_tracker") -> Path:
    """Create a launchable Python entry under ``project/dist/`` for E2E tests."""
    dist_dir = workspace.project_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)
    launcher = dist_dir / f"{safe_name}_launcher.py"
    launcher.write_text(
        '''"""Headless launcher used when PyInstaller is unavailable in CI."""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

main = Path(__file__).resolve().parent.parent / "main.py"
month = date.today().strftime("%Y-%m")
raise SystemExit(
    subprocess.call(
        [sys.executable, str(main), "--cli", "summary", "--month", month],
        cwd=str(main.parent),
    )
)
''',
        encoding="utf-8",
    )
    return launcher


def write_mock_build_report(
    workspace: Workspace,
    *,
    project_name: str = "expense_tracker",
    artifact_rel: str | None = None,
) -> BuildReport:
    """Persist a synthetic ``BUILD_REPORT.json`` and minimal release zip."""
    import hashlib

    dist = workspace.dist_dir
    dist.mkdir(parents=True, exist_ok=True)
    platform = platform_tag()
    archive_name = f"{project_name}-v1.0.0-{platform}.zip"
    zip_path = dist / archive_name

    project_dir = workspace.project_dir
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(project_dir.rglob("*.py")):
            if path.is_file() and "__pycache__" not in path.parts:
                arc = Path("project") / path.relative_to(project_dir)
                zf.write(path, arc.as_posix())

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    report = BuildReport(
        project_name=project_name,
        version="1.0.0",
        platform=platform,
        requirements_path="requirements.txt",
        artifact_path=artifact_rel,
        package_path=f"dist/{archive_name}",
        checksum_sha256=digest,
        smoke_ok=True,
        status="success" if artifact_rel else "partial",
    )
    (dist / "BUILD_REPORT.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def assert_session_cost_under_budget(
    summary: BuildMetricsSummary,
    *,
    max_usd: float = 15.0,
) -> None:
    """Raise when estimated session LLM cost exceeds *max_usd*."""
    if summary.total_cost_usd > max_usd:
        raise AssertionError(
            f"Session cost ${summary.total_cost_usd:.4f} exceeds budget ${max_usd:.2f}"
        )


async def validate_launchable_artifact(
    project_dir: Path,
    artifact: Path,
) -> LaunchValidation:
    """Smoke-launch a built artifact or Python launcher."""
    from agent_builder.devops.build_executor import smoke_test_executable
    from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox

    outcome = LaunchValidation()
    if not artifact.is_file():
        outcome.ok = False
        outcome.errors.append(f"artifact not found: {artifact}")
        return outcome

    sandbox = SubprocessSandbox(project_dir, timeout=30.0)
    if artifact.suffix.lower() == ".exe":
        ok, msg = await smoke_test_executable(artifact, sandbox)
        outcome.ok = ok
        outcome.message = msg
        if not ok:
            outcome.errors.append(msg or "exe smoke failed")
        return outcome

    from agent_builder.validation.project_output import run_entry_script

    code, stdout, stderr, blocked, reason = await run_entry_script(
        sandbox,
        artifact,
        [],
        cwd=project_dir,
    )
    outcome.message = (stdout + stderr)[:200]
    if blocked:
        outcome.ok = False
        outcome.errors.append(reason or "launch blocked")
    elif code != 0:
        outcome.ok = False
        outcome.errors.append(f"launcher exit {code}: {stderr or stdout}")
    return outcome
