import pytest

from agent_builder.agents.plan_parser import (
    PlanParseError,
    enrich_plan,
    estimate_complexity,
    extract_json_payload,
    infer_risks,
    parse_plan,
    validate_plan,
)
from agent_builder.core.state import Plan, PlanTask, TechStack

VALID_PLAN_JSON = """
{
  "project_name": "calc_cli",
  "description": "A simple CLI calculator",
  "tech_stack": {"gui": "none", "storage": null},
  "milestones": [{"id": "M1", "name": "Core", "tasks": ["T1.1"]}],
  "tasks": [
    {
      "id": "T1.1",
      "title": "Calculator script",
      "type": "logic",
      "depends_on": [],
      "files_affected": ["calc.py"],
      "acceptance_criteria": ["Runs without syntax errors"]
    }
  ],
  "estimated_complexity": "small",
  "risks": ["Invalid user input"]
}
"""


def test_extract_json_from_fence() -> None:
    text = 'Here is the plan:\n```json\n{"a": 1}\n```\n'
    assert extract_json_payload(text) == '{"a": 1}'


def test_extract_json_bare_object() -> None:
    assert extract_json_payload('{"project_name": "x"}') == '{"project_name": "x"}'


def test_extract_json_empty_raises() -> None:
    with pytest.raises(PlanParseError, match="Empty"):
        extract_json_payload("   ")


def test_parse_plan_valid() -> None:
    plan = parse_plan(VALID_PLAN_JSON)
    assert plan.project_name == "calc_cli"
    assert len(plan.tasks) == 1
    assert plan.estimated_complexity == "small"


def test_parse_plan_invalid_json() -> None:
    with pytest.raises(PlanParseError, match="Invalid JSON"):
        parse_plan("{not json")


def test_parse_plan_missing_tasks() -> None:
    with pytest.raises(PlanParseError, match="at least one task"):
        parse_plan(
            '{"project_name": "x", "description": "d", '
            '"tasks": [], "estimated_complexity": "small", "risks": []}'
        )


def test_validate_plan_unknown_dependency() -> None:
    plan = Plan(
        project_name="x",
        description="d",
        tasks=[
            PlanTask(
                id="T1.1",
                title="A",
                type="logic",
                depends_on=["T9.9"],
                acceptance_criteria=["ok"],
            )
        ],
        estimated_complexity="small",
    )
    issues = validate_plan(plan)
    assert any("unknown id" in issue for issue in issues)


def test_estimate_complexity() -> None:
    assert estimate_complexity(2) == "small"
    assert estimate_complexity(5) == "medium"
    assert estimate_complexity(12) == "large"


def test_infer_risks_flet() -> None:
    plan = Plan(
        project_name="app",
        description="d",
        tech_stack=TechStack(gui="flet"),
        tasks=[
            PlanTask(
                id="T1.1",
                title="UI",
                type="ui",
                acceptance_criteria=["renders"],
            )
        ],
    )
    risks = infer_risks(plan)
    assert any("Flet" in r for r in risks)


def test_enrich_plan_adds_risks_when_empty() -> None:
    plan = Plan(
        project_name="app",
        description="d",
        tech_stack=TechStack(gui="flet"),
        tasks=[
            PlanTask(
                id="T1.1",
                title="UI",
                type="ui",
                acceptance_criteria=["renders"],
            )
        ],
        risks=[],
    )
    enriched = enrich_plan(plan)
    assert enriched.risks
