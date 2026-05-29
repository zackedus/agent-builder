"""Parse Designer LLM output into ``ScreenDesign`` models."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from agent_builder.agents.design_models import FLET_WIDGET_TYPES, ScreenDesign
from agent_builder.agents.plan_parser import PlanParseError, extract_json_payload
from agent_builder.llm.exceptions import LLMError


class DesignParseError(LLMError):
    """Failed to parse designer output."""


def parse_design(text: str) -> ScreenDesign:
    """Parse LLM output into a validated ``ScreenDesign``."""
    try:
        payload = extract_json_payload(text)
    except PlanParseError as exc:
        raise DesignParseError(str(exc)) from exc
    try:
        data: Any = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DesignParseError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise DesignParseError("Design root must be a JSON object")

    try:
        design = ScreenDesign.model_validate(data)
    except ValidationError as exc:
        raise DesignParseError(f"Design schema validation failed: {exc}") from exc

    issues = validate_design_semantics(design)
    if issues:
        raise DesignParseError("; ".join(issues))
    return design


def validate_design_semantics(design: ScreenDesign) -> list[str]:
    """Return human-readable validation issues (empty if valid)."""
    issues: list[str] = []
    if not design.screen_id.strip():
        issues.append("screen_id is required")
    if not design.title.strip():
        issues.append("title is required")
    if not design.widgets:
        issues.append("at least one widget is required")

    seen_ids: set[str] = set()
    for widget in design.widgets:
        if not widget.id.strip():
            issues.append("widget id is required")
        elif widget.id in seen_ids:
            issues.append(f"duplicate widget id: {widget.id}")
        else:
            seen_ids.add(widget.id)
        if widget.type not in FLET_WIDGET_TYPES:
            issues.append(f"unknown widget type: {widget.type}")

    return issues


def format_design_for_coder(design: ScreenDesign) -> str:
    """Compact summary for Coder prompt context."""
    lines = [
        f"Screen: {design.screen_id} — {design.title}",
        f"Layout: {design.layout}",
        "Widgets:",
    ]
    for widget in design.widgets:
        label = f" ({widget.label})" if widget.label else ""
        lines.append(f"  - {widget.type} id={widget.id}{label}")
    if design.navigation:
        nav = design.navigation
        parts = []
        if nav.back_to:
            parts.append(f"back_to={nav.back_to}")
        if nav.next_on_success:
            parts.append(f"next_on_success={nav.next_on_success}")
        if parts:
            lines.append("Navigation: " + ", ".join(parts))
    return "\n".join(lines)
