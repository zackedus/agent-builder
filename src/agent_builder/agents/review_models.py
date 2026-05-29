"""Pydantic models for Reviewer output (``reviews/{task_id}.json``)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ReviewVerdict = Literal["approved", "changes_requested", "rejected"]
IssueSeverity = Literal["high", "medium", "low"]
IssueType = Literal["security", "bug", "style", "architecture", "other"]


class ReviewIssue(BaseModel):
    severity: IssueSeverity
    type: IssueType = "other"
    file: str = ""
    line: int | None = None
    description: str
    suggestion: str = ""


class ReviewResult(BaseModel):
    """Reviewer output persisted per task."""

    task_id: str
    verdict: ReviewVerdict
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str = ""

    def requires_changes(self) -> bool:
        return self.verdict in ("changes_requested", "rejected")

    def blocking_issues(self) -> list[ReviewIssue]:
        return [i for i in self.issues if i.severity == "high"]
