"""Unit tests for pytest coverage extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_builder.agents.test_runner import (
    COVERAGE_JSON_NAME,
    parse_coverage_json,
    run_pytest,
)
from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox


def test_parse_coverage_json_reads_totals(tmp_path: Path) -> None:
    path = tmp_path / "cov.json"
    path.write_text(
        json.dumps({"totals": {"percent_covered": 78.5}}),
        encoding="utf-8",
    )
    assert parse_coverage_json(path) == 78.5


def test_parse_coverage_json_aggregates_files(tmp_path: Path) -> None:
    path = tmp_path / "cov.json"
    path.write_text(
        json.dumps(
            {
                "files": {
                    "a.py": {"summary": {"covered_lines": 8, "num_statements": 10}},
                    "b.py": {"summary": {"covered_lines": 5, "num_statements": 10}},
                }
            }
        ),
        encoding="utf-8",
    )
    assert parse_coverage_json(path) == 65.0


def test_parse_coverage_json_missing_file() -> None:
    assert parse_coverage_json(Path("/nonexistent/cov.json")) is None


@pytest.mark.asyncio
async def test_run_pytest_extracts_coverage(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "adder.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n",
        encoding="utf-8",
    )
    tests = project / "tests"
    tests.mkdir()
    (tests / "test_adder.py").write_text(
        "from adder import add\n\ndef test_add() -> None:\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )

    sandbox = SubprocessSandbox(project)
    result = await run_pytest(project, sandbox)
    assert result.summary.total >= 1
    assert result.summary.failed == 0
    if result.coverage_percent is not None:
        assert result.coverage_percent >= 50.0
    assert not (project / COVERAGE_JSON_NAME).exists()
