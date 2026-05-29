"""Unit tests for release packaging."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from agent_builder.devops.lockfile import generate_requirements_lock
from agent_builder.devops.models import BuildReport
from agent_builder.devops.packager import create_release_package, write_build_report


def test_create_release_package_writes_zip_and_checksum(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("print('hello')\n", encoding="utf-8")
    generate_requirements_lock(project)

    dist = tmp_path / "dist"
    report = BuildReport(
        project_name="todo-app",
        version="1.0.0",
        platform="win64",
        requirements_path="requirements.txt",
        notes=["test build"],
    )
    zip_path = create_release_package(dist, project, report)

    assert zip_path.is_file()
    assert report.checksum_sha256
    assert report.package_path == "dist/todo-app-v1.0.0-win64.zip"
    assert (dist / "README_RELEASE.md").is_file()
    assert (zip_path.with_suffix(zip_path.suffix + ".sha256")).is_file()

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "project/main.py" in names
        assert "README_RELEASE.md" in names


def test_write_build_report_persists_json(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    report = BuildReport(
        project_name="app",
        version="0.1.0",
        platform="linux",
        requirements_path="requirements.txt",
        package_path="dist/app.zip",
        status="partial",
    )
    path = write_build_report(dist, report)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["project_name"] == "app"
    assert data["status"] == "partial"
