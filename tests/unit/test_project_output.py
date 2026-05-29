from pathlib import Path

import pytest

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import SessionState
from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox
from agent_builder.validation.project_output import (
    assert_calculator_output,
    find_entry_script,
    find_python_files,
    summarize_metrics_from_events,
    validate_project_output,
    validate_python_syntax,
)


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    calc_src = (
        "import sys\n\n"
        'if __name__ == "__main__":\n'
        "    print(float(sys.argv[1]) * float(sys.argv[2]))\n"
    )
    (project / "calc.py").write_text(calc_src, encoding="utf-8")
    return project


def test_find_python_files(sample_project: Path) -> None:
    files = find_python_files(sample_project)
    assert len(files) == 1
    assert files[0].name == "calc.py"


def test_validate_python_syntax_ok(sample_project: Path) -> None:
    files = find_python_files(sample_project)
    assert validate_python_syntax(files) == []


def test_find_entry_script_prefers_calc(sample_project: Path) -> None:
    files = find_python_files(sample_project)
    entry = find_entry_script(sample_project, files)
    assert entry is not None
    assert entry.name == "calc.py"


@pytest.mark.asyncio
async def test_validate_project_output_runs(sample_project: Path) -> None:
    sandbox = SubprocessSandbox(sample_project)
    result = await validate_project_output(
        sample_project,
        run_args=["3", "4"],
        sandbox=sandbox,
    )
    assert result.syntax_ok
    assert result.run_ok
    assert_calculator_output(result.run_stdout, 12.0)


def test_assert_calculator_output_fails_on_empty() -> None:
    with pytest.raises(AssertionError):
        assert_calculator_output("no numbers here", 5.0)


def test_summarize_metrics_from_events() -> None:
    session = SessionState(user_prompt="x")
    events = [
        Event(
            type=EventType.LLM_CALL,
            session_id=session.session_id,
            payload={
                "model": "claude-sonnet-4-6",
                "input_tokens": 1000,
                "output_tokens": 500,
            },
        ),
    ]
    summary = summarize_metrics_from_events(events, session)
    assert summary.total_llm_calls == 1
    assert summary.total_cost_usd > 0
    assert summary.input_tokens == 1000
