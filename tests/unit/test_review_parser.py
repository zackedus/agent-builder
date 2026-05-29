import pytest

from agent_builder.agents.review_models import ReviewResult
from agent_builder.agents.review_parser import (
    ReviewParseError,
    format_review_feedback,
    parse_review,
)

VALID_REVIEW = """
{
  "task_id": "T1.1",
  "verdict": "changes_requested",
  "issues": [
    {
      "severity": "high",
      "type": "security",
      "file": "calc.py",
      "line": 10,
      "description": "Use argparse instead of raw argv",
      "suggestion": "import argparse"
    }
  ],
  "summary": "One security concern."
}
"""


def test_parse_review_valid() -> None:
    review = parse_review(VALID_REVIEW, task_id="T1.1")
    assert review.verdict == "changes_requested"
    assert review.issues[0].severity == "high"


def test_parse_review_injects_task_id() -> None:
    review = parse_review('{"verdict": "approved", "summary": "ok"}', task_id="T9")
    assert review.task_id == "T9"


def test_format_review_feedback() -> None:
    review = ReviewResult.model_validate_json(VALID_REVIEW)
    text = format_review_feedback(review)
    assert "security" in text
    assert "argparse" in text


def test_parse_review_invalid() -> None:
    with pytest.raises(ReviewParseError):
        parse_review("not json", task_id="T1")
