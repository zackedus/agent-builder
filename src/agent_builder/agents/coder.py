"""Coder agent — implement tasks in workspace/project/."""

from __future__ import annotations

import ast

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
from agent_builder.agents.code_parser import CodeParseError, extract_code_files
from agent_builder.core.state import Plan, PlanTask
from agent_builder.llm.types import LLMMessage
from agent_builder.tools.file_ops import write_project_files

CODER_SYSTEM = """You are the Coder agent for Agent Team Builder.
Output source files using markdown code fences with filenames.
Example: ```python:main.py
print("hello")
```
No prose outside code fences."""


class CoderAgent(BaseAgent):
    """Writes generated source files into ``workspace/project/``."""

    name = "coder"
    max_retries = 3

    async def execute(self, context: AgentContext) -> AgentResult:
        if self.workspace is None:
            return AgentResult(success=False, output="Workspace is required for Coder")

        plan = context.extra.get("plan")
        plan_task: PlanTask | None = context.extra.get("plan_task")
        feedback = str(context.extra.get("feedback", ""))

        files_hint = ""
        if plan_task and plan_task.files_affected:
            files_hint = ", ".join(plan_task.files_affected)
        elif plan_task:
            files_hint = "(infer from task title)"

        plan_context = _format_plan_context(plan, plan_task)
        if feedback:
            plan_context = f"{plan_context}\n\nPrevious attempt errors:\n{feedback}"

        prompt = self.load_prompt(
            "coder",
            task_id=context.task_id or (plan_task.id if plan_task else ""),
            task_title=context.task_title or (plan_task.title if plan_task else ""),
            task_type=context.task_type,
            user_prompt=context.user_prompt,
            context=plan_context,
            files_affected=files_hint or "—",
        )
        messages = [LLMMessage(role="user", content=prompt)]

        task_type = context.task_type
        if plan_task and task_type == "default":
            task_type = plan_task.type

        response = await self.complete_llm(
            context,
            messages,
            system=CODER_SYSTEM,
            max_tokens=8000,
            task_type=task_type,
        )

        default_paths = list(plan_task.files_affected) if plan_task else None
        try:
            code_files = extract_code_files(response.text, default_paths=default_paths)
        except CodeParseError as exc:
            return AgentResult(
                success=False,
                output=str(exc),
                data={"raw": response.text},
                last_model=response.model,
            )

        syntax_errors: list[str] = []
        for code_file in code_files:
            if code_file.path.endswith(".py"):
                try:
                    ast.parse(code_file.content, filename=code_file.path)
                except SyntaxError as exc:
                    syntax_errors.append(f"{code_file.path}: {exc}")

        if syntax_errors:
            return AgentResult(
                success=False,
                output="; ".join(syntax_errors),
                data={"raw": response.text, "code_files": code_files},
                last_model=response.model,
            )

        written = write_project_files(
            self.workspace,
            {cf.path: cf.content for cf in code_files},
        )

        return AgentResult(
            success=False,
            output=response.text,
            data={
                "files": [str(p.relative_to(self.workspace.project_dir)) for p in written],
                "code_files": code_files,
                "raw": response.text,
            },
            last_model=response.model,
        )

    def validate_result(self, result: AgentResult) -> bool:
        files = result.data.get("files")
        return isinstance(files, list) and len(files) > 0


def _format_plan_context(plan: object, task: PlanTask | None) -> str:
    if not isinstance(plan, Plan):
        if task:
            return f"Task: {task.title}\nAcceptance: {', '.join(task.acceptance_criteria)}"
        return "No plan loaded."

    lines = [
        f"Project: {plan.project_name}",
        f"Description: {plan.description}",
        f"Tech stack: {plan.tech_stack.model_dump_json()}",
    ]
    if task:
        lines.extend(
            [
                f"Current task: {task.id} — {task.title}",
                f"Acceptance criteria: {'; '.join(task.acceptance_criteria)}",
            ]
        )
    return "\n".join(lines)
