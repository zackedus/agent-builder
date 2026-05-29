"""Pydantic models for Tester output (``test_results/{task_id}.json``)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TestStatus = Literal["passed", "failed", "partial"]
CheckStatus = Literal["passed", "failed", "skipped"]


class TestFailure(BaseModel):
    test_name: str
    error: str
    traceback: str = ""


class TestRunSummary(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    failures: list[TestFailure] = Field(default_factory=list)


class TesterReport(BaseModel):
    """Tester output persisted per task."""

    __test__ = False

    task_id: str
    status: TestStatus
    static_checks: dict[str, CheckStatus] = Field(default_factory=dict)
    static_output: dict[str, str] = Field(default_factory=dict)
    tests: TestRunSummary = Field(default_factory=TestRunSummary)
    smoke: CheckStatus = "skipped"
    smoke_output: str = ""
    coverage: float | None = None

    def is_passing(self) -> bool:
        return self.status == "passed"
