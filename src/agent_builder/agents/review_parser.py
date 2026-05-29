"""Parse Reviewer LLM output into ``ReviewResult`` models."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from agent_builder.agents.plan_parser import PlanParseError, extract_json_payload
from agent_builder.agents.review_models import ReviewResult
from agent_builder.llm.exceptions import LLMError


class ReviewParseError(LLMError):
    """Failed to parse reviewer output."""


def parse_review(text: str, *, task_id: str) -> ReviewResult:
    """Parse LLM output into a validated ``ReviewResult``."""
    try:
        payload = extract_json_payload(text)
    except PlanParseError as exc:
        raise ReviewParseError(str(exc)) from exc
    try:
        data: Any = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ReviewParseError(f"Invalid JSON: {exc}") from exc

    if isinstance(data, dict) and "task_id" not in data:
        data["task_id"] = task_id

    try:
        return ReviewResult.model_validate(data)
    except ValidationError as exc:
        raise ReviewParseError(f"Review schema validation failed: {exc}") from exc


def format_review_feedback(review: ReviewResult) -> str:
    """Human-readable notes for Coder retry context."""
    lines = [f"Review verdict: {review.verdict}", review.summary]
    for issue in review.issues:
        loc = issue.file
        if issue.line is not None:
            loc = f"{loc}:{issue.line}"
        lines.append(f"[{issue.severity}/{issue.type}] {loc}: {issue.description}")
        if issue.suggestion:
            lines.append(f"  Suggestion: {issue.suggestion}")
    return "\n".join(line for line in lines if line.strip())
