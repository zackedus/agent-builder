"""UI/UX designer agent — design.json for Flet screens."""

from __future__ import annotations

from pathlib import Path

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
from agent_builder.agents.design_models import ScreenDesign
from agent_builder.agents.design_parser import (
    DesignParseError,
    format_design_for_coder,
    parse_design,
)
from agent_builder.config import Settings, get_settings
from agent_builder.core.state import Plan, PlanTask
from agent_builder.core.workspace import Workspace, atomic_write_json
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage

DESIGNER_SYSTEM = """You are the UI/UX Designer for Agent Team Builder.
Output ONLY valid JSON for one Flet screen spec. Use Flet widget names exactly.
No prose outside JSON."""


class DesignerAgent(BaseAgent):
    """Produces ``designs/{task_id}.json`` for UI tasks."""

    name = "designer"
    max_retries = 2

    def __init__(
        self,
        router: LLMRouter,
        workspace: Workspace | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(router, workspace)
        self.settings = settings or get_settings()

    async def execute(self, context: AgentContext) -> AgentResult:
        if self.workspace is None:
            return AgentResult(success=False, output="Workspace is required for Designer")

        plan = context.extra.get("plan")
        plan_task: PlanTask | None = context.extra.get("plan_task")
        task_id = context.task_id or (plan_task.id if plan_task else "unknown")

        acceptance = "—"
        if plan_task and plan_task.acceptance_criteria:
            acceptance = "\n".join(f"- {c}" for c in plan_task.acceptance_criteria)

        prompt = self.load_prompt(
            "designer",
            task_id=task_id,
            task_title=context.task_title or (plan_task.title if plan_task else ""),
            user_prompt=context.user_prompt or "—",
            plan_context=_plan_summary(plan, plan_task),
            acceptance_criteria=acceptance,
        )
        messages = [LLMMessage(role="user", content=prompt)]

        response = await self.complete_llm(
            context,
            messages,
            system=DESIGNER_SYSTEM,
            max_tokens=4000,
            task_type="ui",
        )

        try:
            design = parse_design(response.text)
        except DesignParseError as exc:
            return AgentResult(
                success=False,
                output=str(exc),
                data={"raw": response.text},
                last_model=response.model,
            )

        path = self._save_design(task_id, design)

        return AgentResult(
            success=False,
            output=format_design_for_coder(design),
            data={
                "design": design,
                "design_path": str(path.relative_to(self.workspace.root)).replace("\\", "/"),
                "raw": response.text,
            },
            last_model=response.model,
        )

    def validate_result(self, result: AgentResult) -> bool:
        design = result.data.get("design")
        return isinstance(design, ScreenDesign)

    def _save_design(self, task_id: str, design: ScreenDesign) -> Path:
        assert self.workspace is not None
        path = self.workspace.design_path(task_id)
        atomic_write_json(path, design.model_dump(mode="json"))
        return path


def _plan_summary(plan: object, task: PlanTask | None) -> str:
    if not isinstance(plan, Plan):
        if task:
            return f"Task: {task.title}"
        return "No plan loaded."
    lines = [f"Project: {plan.project_name}", f"Description: {plan.description}"]
    if task:
        lines.append(f"Current task: {task.id} — {task.title}")
    return "\n".join(lines)


def load_design_for_task(workspace: Workspace, task_id: str) -> ScreenDesign | None:
    """Load persisted design spec for *task_id*, if present."""
    path = workspace.design_path(task_id)
    if not path.is_file():
        return None
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        return ScreenDesign.model_validate(data)
    except (OSError, ValueError):
        return None
