"""Workspace path management and atomic JSON persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from agent_builder.core.events_store import EventsStore
from agent_builder.core.exceptions import WorkspaceError
from agent_builder.core.state import Plan, SessionState, plan_from_json, session_state_from_json

TModel = TypeVar("TModel", bound=BaseModel)


class Workspace:
    """Manages session workspace layout (ARCHITECTURE.md §8)."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.agent_dir = self.root / ".agent"
        self.project_dir = self.root / "project"
        self.dist_dir = self.root / "dist"
        self.state_path = self.agent_dir / "state.json"
        self.plan_path = self.agent_dir / "plan.json"
        self.events_path = self.agent_dir / "events.jsonl"
        self.designs_dir = self.agent_dir / "designs"
        self.reviews_dir = self.agent_dir / "reviews"
        self.test_results_dir = self.agent_dir / "test_results"
        self.logs_dir = self.agent_dir / "logs"
        self.vectordb_dir = self.agent_dir / ".vectordb"

    def ensure_layout(self) -> None:
        """Create standard workspace directories if missing."""
        for directory in (
            self.agent_dir,
            self.designs_dir,
            self.reviews_dir,
            self.test_results_dir,
            self.logs_dir,
            self.vectordb_dir,
            self.project_dir,
            self.dist_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def load_session(self) -> SessionState | None:
        """Load session state from disk, or ``None`` if no session exists."""
        if not self.state_path.is_file():
            return None
        try:
            return session_state_from_json(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise WorkspaceError(f"Failed to load session state: {self.state_path}") from exc

    def save_session(self, state: SessionState) -> None:
        """Persist session state atomically."""
        self.ensure_layout()
        atomic_write_model(self.state_path, state)

    def load_plan(self) -> Plan | None:
        if not self.plan_path.is_file():
            return None
        try:
            return plan_from_json(self.plan_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise WorkspaceError(f"Failed to load plan: {self.plan_path}") from exc

    def save_plan(self, plan: Plan) -> None:
        self.ensure_layout()
        atomic_write_model(self.plan_path, plan)

    def review_path(self, task_id: str) -> Path:
        return self.reviews_dir / f"{task_id}.json"

    def test_result_path(self, task_id: str) -> Path:
        return self.test_results_dir / f"{task_id}.json"

    def design_path(self, screen_id: str) -> Path:
        return self.designs_dir / f"{screen_id}.json"

    def events_store(self) -> EventsStore:
        return EventsStore(self.events_path)


def atomic_write_text(path: Path, content: str) -> None:
    """Write text atomically via temp file + replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(path)
    except OSError as exc:
        tmp_path.unlink(missing_ok=True)
        raise WorkspaceError(f"Failed to write file atomically: {path}") from exc


def atomic_write_json(path: Path, data: dict[str, Any] | list[Any], *, indent: int = 2) -> None:
    """Serialize JSON and write atomically."""
    payload = json.dumps(data, indent=indent, ensure_ascii=False) + "\n"
    atomic_write_text(path, payload)


def atomic_write_model(path: Path, model: BaseModel, *, indent: int = 2) -> None:
    """Serialize a Pydantic model to JSON and write atomically."""
    data = model.model_dump(mode="json")
    atomic_write_json(path, data, indent=indent)
