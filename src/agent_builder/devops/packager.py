"""Zip release artifacts with checksum and README."""

from __future__ import annotations

import hashlib
import platform
import zipfile
from pathlib import Path

from agent_builder.devops.models import BuildReport


def platform_tag() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "win64"
    if system == "darwin":
        return "macos"
    return "linux"


def create_release_package(
    workspace_dist: Path,
    project_dir: Path,
    report: BuildReport,
) -> Path:
    """Create ``dist/{project}-v{version}-{platform}.zip`` and update *report* checksum."""
    workspace_dist.mkdir(parents=True, exist_ok=True)
    archive_name = f"{report.project_name}-v{report.version}-{report.platform}.zip"
    zip_path = workspace_dist / archive_name

    readme = _release_readme(report)
    readme_path = workspace_dist / "README_RELEASE.md"
    readme_path.write_text(readme, encoding="utf-8")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(project_dir.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                arcname = Path("project") / path.relative_to(project_dir)
                zf.write(path, arcname.as_posix())
        if report.artifact_path:
            artifact = Path(report.artifact_path)
            if not artifact.is_absolute():
                artifact = project_dir / artifact
            if artifact.is_file():
                zf.write(artifact, f"bin/{artifact.name}")
        zf.write(readme_path, "README_RELEASE.md")

    checksum = _sha256_file(zip_path)
    checksum_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
    checksum_path.write_text(f"{checksum}  {zip_path.name}\n", encoding="utf-8")

    report.checksum_sha256 = checksum
    report.package_path = str(zip_path.relative_to(workspace_dist.parent)).replace("\\", "/")
    return zip_path


def write_build_report(workspace_dist: Path, report: BuildReport) -> Path:
    """Persist ``BUILD_REPORT.json`` under *workspace_dist*."""
    import json

    workspace_dist.mkdir(parents=True, exist_ok=True)
    path = workspace_dist / "BUILD_REPORT.json"
    path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _release_readme(report: BuildReport) -> str:
    lines = [
        f"# {report.project_name} v{report.version}",
        "",
        f"Platform: {report.platform}",
        f"Build status: {report.status}",
        "",
        "## Contents",
        "- `project/` — application source",
        "- `bin/` — built executable (if PyInstaller succeeded)",
        "",
        "## Install dependencies",
        "```bash",
        "pip install -r project/requirements.txt",
        "```",
        "",
        "## Checksum",
        f"SHA256: {report.checksum_sha256 or '(see .sha256 file)'}",
        "",
    ]
    if report.notes:
        lines.append("## Notes")
        lines.extend(f"- {note}" for note in report.notes)
    return "\n".join(lines) + "\n"
