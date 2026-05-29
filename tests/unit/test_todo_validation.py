"""Unit tests for todo project validation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_builder.core.event_bus import Event, EventType
from agent_builder.validation.project_output import count_self_corrections


def test_count_self_corrections_from_events() -> None:
    events = [
        Event(
            type=EventType.STATE_CHANGED,
            session_id="s1",
            payload={"from": "TESTING", "to": "CODING", "event": "tests_fail"},
        ),
        Event(
            type=EventType.STATE_CHANGED,
            session_id="s1",
            payload={"from": "CODING", "to": "TESTING", "event": "code_written"},
        ),
        Event(
            type=EventType.STATE_CHANGED,
            session_id="s1",
            payload={"from": "REVIEWING", "to": "CODING", "event": "changes_requested"},
        ),
    ]
    assert count_self_corrections(events) == 2


@pytest.mark.asyncio
async def test_validate_todo_crud_on_fixture_code(tmp_path: Path) -> None:
    from agent_builder.agents.code_parser import extract_code_files
    from agent_builder.validation.project_output import validate_todo_crud
    from tests.e2e.fixtures.todo_responses import TODO_CODE_V2

    project = tmp_path / "project"
    project.mkdir()
    for code_file in extract_code_files(
        TODO_CODE_V2,
        default_paths=["todo_store.py", "main.py"],
    ):
        dest = project / code_file.path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code_file.content, encoding="utf-8")

    result = await validate_todo_crud(project)
    assert result.steps_ok, result.errors
