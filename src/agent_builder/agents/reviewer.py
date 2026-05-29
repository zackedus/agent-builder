"""Reviewer agent — semantic code review via LLM."""

from __future__ import annotations

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
from agent_builder.agents.review_models import ReviewResult
from agent_builder.agents.review_parser import (
    ReviewParseError,
    format_review_feedback,
    parse_review,
)
from agent_builder.core.state import Plan, PlanTask
from agent_builder.core.workspace import Workspace, atomic_write_json
from agent_builder.llm.types import LLMMessage
from agent_builder.tools.file_ops import read_project_file

REVIEWER_SYSTEM = """You are the Reviewer agent for Agent Team Builder.
Output ONLY valid JSON matching the review schema. No markdown outside a json code block.
Be strict on security and plan adherence. Use verdict: approved | changes_requested | rejected."""


class ReviewerAgent(BaseAgent):
    """Reviews generated code and writes ``reviews/{task_id}.json``."""

    name = "reviewer"
    max_retries = 2

    async def execute(self, context: AgentContext) -> AgentResult:
        if self.workspace is None:
            return AgentResult(success=False, output="Workspace is required for Reviewer")

        plan = context.extra.get("plan")
        plan_task: PlanTask | None = context.extra.get("plan_task")
        task_id = context.task_id or (plan_task.id if plan_task else "unknown")

        content = _load_review_content(self.workspace, plan_task)
        acceptance = ""
        if plan_task:
            acceptance = "; ".join(plan_task.acceptance_criteria)

        prompt = self.load_prompt(
            "reviewer",
            task_id=task_id,
            task_title=context.task_title or (plan_task.title if plan_task else ""),
            content=content[:12000],
            acceptance_criteria=acceptance or "—",
            plan_summary=_plan_summary(plan),
        )
        messages = [LLMMessage(role="user", content=prompt)]

        response = await self.complete_llm(
            context,
            messages,
            system=REVIEWER_SYSTEM,
            max_tokens=4000,
            task_type="default",
        )

        try:
            review = parse_review(response.text, task_id=task_id)
        except ReviewParseError as exc:
            return AgentResult(
                success=False,
                output=str(exc),
                data={"raw": response.text},
                last_model=response.model,
            )

        path = self.workspace.review_path(task_id)
        atomic_write_json(path, review.model_dump(mode="json"))

        return AgentResult(
            success=False,
            output=format_review_feedback(review),
            data={"review": review, "raw": response.text},
            last_model=response.model,
        )

    def validate_result(self, result: AgentResult) -> bool:
        review = result.data.get("review")
        return isinstance(review, ReviewResult) and review.verdict == "approved"


def _load_review_content(workspace: Workspace, plan_task: PlanTask | None) -> str:
    project_dir = workspace.project_dir
    if plan_task is None or not plan_task.files_affected:
        py_files = sorted(project_dir.rglob("*.py"))[:5]
        chunks: list[str] = []
        for path in py_files:
            rel = path.relative_to(project_dir)
            chunks.append(f"### {rel}\n```python\n{path.read_text(encoding='utf-8')[:4000]}\n```")
        return "\n\n".join(chunks) if chunks else "(no files)"

    parts: list[str] = []
    for rel_path in plan_task.files_affected:
        try:
            body = read_project_file(workspace, rel_path)
        except Exception:
            file_path = project_dir / rel_path
            body = file_path.read_text(encoding="utf-8") if file_path.is_file() else "(missing)"
        parts.append(f"### {rel_path}\n```python\n{body[:4000]}\n```")
    return "\n\n".join(parts)


def _plan_summary(plan: object) -> str:
    if not isinstance(plan, Plan):
        return "—"
    return f"{plan.project_name}: {plan.description[:300]}"
