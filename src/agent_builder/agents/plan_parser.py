"""Parse and validate Planner LLM output into ``Plan`` models."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from agent_builder.core.state import Complexity, Plan
from agent_builder.llm.exceptions import LLMError

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


class PlanParseError(LLMError):
    """Failed to parse planner output as a valid plan."""


def extract_json_payload(text: str) -> str:
    """Extract JSON string from raw LLM text (markdown fence or bare object)."""
    stripped = text.strip()
    if not stripped:
        raise PlanParseError("Empty planner response")

    fence_match = _JSON_FENCE_RE.search(stripped)
    if fence_match:
        return fence_match.group(1).strip()

    if stripped.startswith("{"):
        return stripped

    object_match = _JSON_OBJECT_RE.search(stripped)
    if object_match:
        return object_match.group(0)

    raise PlanParseError("No JSON object found in planner response")


def parse_plan(text: str) -> Plan:
    """Parse LLM output into a validated ``Plan``."""
    payload = extract_json_payload(text)
    try:
        data: Any = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PlanParseError(f"Invalid JSON: {exc}") from exc

    try:
        plan = Plan.model_validate(data)
    except ValidationError as exc:
        raise PlanParseError(f"Plan schema validation failed: {exc}") from exc

    issues = validate_plan(plan)
    if issues:
        raise PlanParseError("; ".join(issues))

    return enrich_plan(plan)


def validate_plan(plan: Plan) -> list[str]:
    """Return human-readable validation issues (empty if valid)."""
    issues: list[str] = []

    if not plan.project_name.strip():
        issues.append("project_name is required")
    if not plan.description.strip():
        issues.append("description is required")
    if not plan.tasks:
        issues.append("at least one task is required")

    seen_ids: set[str] = set()
    for task in plan.tasks:
        if not task.id.strip():
            issues.append("task id must not be empty")
        elif task.id in seen_ids:
            issues.append(f"duplicate task id: {task.id}")
        else:
            seen_ids.add(task.id)

        if not task.title.strip():
            issues.append(f"task {task.id} missing title")
        if not task.type.strip():
            issues.append(f"task {task.id} missing type")
        if not task.acceptance_criteria:
            issues.append(f"task {task.id} missing acceptance_criteria")

    for task in plan.tasks:
        for dep in task.depends_on:
            if dep not in seen_ids:
                issues.append(f"task {task.id} depends on unknown id {dep}")

    if plan.estimated_complexity not in ("small", "medium", "large"):
        issues.append(f"invalid estimated_complexity: {plan.estimated_complexity}")

    return issues


def estimate_complexity(task_count: int) -> Complexity:
    """Heuristic complexity from number of tasks."""
    if task_count <= 3:
        return "small"
    if task_count <= 10:
        return "medium"
    return "large"


def infer_risks(plan: Plan) -> list[str]:
    """Suggest risks when the model omits them."""
    risks: list[str] = []
    gui = (plan.tech_stack.gui or "").lower()
    if "flet" in gui:
        risks.append("Flet API changes or PyInstaller packaging compatibility")
    if len(plan.tasks) > 15:
        risks.append("Large task count may increase session cost and duration")
    if any(t.type == "logic" for t in plan.tasks):
        risks.append("Business logic may need clarification from user")
    return risks


def enrich_plan(plan: Plan) -> Plan:
    """Fill derived fields: risks, complexity alignment."""
    computed = estimate_complexity(len(plan.tasks))
    risks = list(plan.risks) if plan.risks else infer_risks(plan)

    updates: dict[str, Any] = {}
    if not plan.risks:
        updates["risks"] = risks
    if plan.estimated_complexity != computed and len(plan.tasks) > 0:
        # Keep model value but ensure it is valid; nudge only when empty tasks edge case
        pass
    if len(plan.tasks) > 0 and plan.estimated_complexity == "medium" and computed != "medium":
        # Document mismatch is OK; optional: prefer computed for very small plans
        if len(plan.tasks) <= 2:
            updates["estimated_complexity"] = computed

    if updates:
        return plan.model_copy(update=updates)
    return plan
