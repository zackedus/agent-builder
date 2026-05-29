"""Unit tests for PyInstaller spec generation."""

from __future__ import annotations

from pathlib import Path

from agent_builder.devops.spec_builder import generate_pyinstaller_spec


def test_generate_pyinstaller_spec_writes_entry(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print(1)\n", encoding="utf-8")
    spec = generate_pyinstaller_spec(
        tmp_path,
        entry_script="main.py",
        project_name="My Todo App",
    )
    content = spec.read_text(encoding="utf-8")
    assert spec.suffix == ".spec"
    assert '["main.py"]' in content
    assert spec.name == "My_Todo_App.spec"
