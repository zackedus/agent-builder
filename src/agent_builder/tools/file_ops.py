"""Safe read/write helpers under ``workspace/project/``."""

from __future__ import annotations

from pathlib import Path

from agent_builder.core.exceptions import WorkspaceError
from agent_builder.core.workspace import Workspace, atomic_write_text


class PathTraversalError(WorkspaceError):
    """Resolved path escapes the project directory."""


def resolve_project_path(workspace: Workspace, relative_path: str) -> Path:
    """Resolve a relative path inside ``workspace.project_dir``."""
    rel = Path(relative_path.replace("\\", "/").lstrip("/"))
    if rel.is_absolute():
        raise PathTraversalError(f"Absolute paths are not allowed: {relative_path}")
    if ".." in rel.parts:
        raise PathTraversalError(f"Path traversal not allowed: {relative_path}")

    project_root = workspace.project_dir.resolve()
    target = (project_root / rel).resolve()
    if target != project_root and project_root not in target.parents:
        raise PathTraversalError(f"Path escapes project root: {relative_path}")
    return target


def write_project_file(workspace: Workspace, relative_path: str, content: str) -> Path:
    """Write a single file under the project directory."""
    path = resolve_project_path(workspace, relative_path)
    atomic_write_text(path, content)
    return path


def write_project_files(workspace: Workspace, files: dict[str, str]) -> list[Path]:
    """Write multiple project files atomically (one file per call)."""
    written: list[Path] = []
    for rel, content in files.items():
        written.append(write_project_file(workspace, rel, content))
    return written


def read_project_file(workspace: Workspace, relative_path: str) -> str:
    """Read a file from the project directory."""
    path = resolve_project_path(workspace, relative_path)
    if not path.is_file():
        raise WorkspaceError(f"Project file not found: {relative_path}")
    return path.read_text(encoding="utf-8")
