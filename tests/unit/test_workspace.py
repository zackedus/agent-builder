import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_builder.core.exceptions import WorkspaceError
from agent_builder.core.state import OrchestratorState, Plan, PlanTask, SessionState
from agent_builder.core.workspace import Workspace, atomic_write_json, atomic_write_text


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "workspace")
    ws.ensure_layout()
    return ws


def test_workspace_layout_directories(workspace: Workspace) -> None:
    assert workspace.agent_dir.is_dir()
    assert workspace.project_dir.is_dir()
    assert workspace.logs_dir.is_dir()
    assert workspace.designs_dir.is_dir()


def test_save_and_load_session(workspace: Workspace) -> None:
    state = SessionState(
        user_prompt="Hello",
        current_state=OrchestratorState.PLANNING,
    )
    workspace.save_session(state)
    loaded = workspace.load_session()
    assert loaded is not None
    assert loaded.session_id == state.session_id
    assert loaded.user_prompt == "Hello"
    assert loaded.current_state == OrchestratorState.PLANNING


def test_load_session_returns_none_when_missing(workspace: Workspace) -> None:
    assert workspace.load_session() is None


def test_save_and_load_plan(workspace: Workspace) -> None:
    plan = Plan(
        project_name="demo",
        description="Demo app",
        tasks=[
            PlanTask(id="T1", title="Setup", type="scaffold"),
        ],
    )
    workspace.save_plan(plan)
    loaded = workspace.load_plan()
    assert loaded is not None
    assert loaded.project_name == "demo"
    assert loaded.tasks[0].id == "T1"


def test_atomic_write_json_no_partial_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "data.json"
    atomic_write_json(target, {"key": "value"})
    assert target.is_file()
    assert json.loads(target.read_text(encoding="utf-8")) == {"key": "value"}
    tmp_files = list(target.parent.glob("*.tmp"))
    assert tmp_files == []


def test_atomic_write_leaves_no_tmp_on_replace_failure(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_text(target, '{"ok": true}\n')

    with patch.object(Path, "replace", side_effect=OSError("replace failed")):
        with pytest.raises(WorkspaceError):
            atomic_write_json(target, {"broken": True})

    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_crash_safety_preserves_previous_session(workspace: Workspace) -> None:
    first = SessionState(user_prompt="first", current_state=OrchestratorState.IDLE)
    second = SessionState(user_prompt="second", current_state=OrchestratorState.PLANNING)
    workspace.save_session(first)

    with patch.object(Path, "replace", side_effect=OSError("simulated crash")):
        with pytest.raises(WorkspaceError):
            workspace.save_session(second)

    restored = workspace.load_session()
    assert restored is not None
    assert restored.user_prompt == "first"
    assert restored.current_state == OrchestratorState.IDLE


def test_workspace_helper_paths(workspace: Workspace) -> None:
    assert workspace.review_path("T1.1") == workspace.reviews_dir / "T1.1.json"
    assert workspace.test_result_path("T2.3") == workspace.test_results_dir / "T2.3.json"
    assert workspace.design_path("home") == workspace.designs_dir / "home.json"
