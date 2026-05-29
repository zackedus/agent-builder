"""Coder agent — implement tasks in workspace/project/."""

from __future__ import annotations

import ast

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
from agent_builder.agents.code_parser import CodeFile, CodeParseError, extract_code_files
from agent_builder.agents.code_patches import PatchApplyError, apply_all_patches
from agent_builder.agents.coder_context import (
    build_coder_search_query,
    collect_context_paths,
    fetch_index_hits,
    format_existing_files_context,
    format_flet_context,
    format_index_context,
)
from agent_builder.agents.design_models import ScreenDesign
from agent_builder.agents.design_parser import format_design_for_coder
from agent_builder.agents.designer import load_design_for_task
from agent_builder.config import Settings, get_settings
from agent_builder.core.exceptions import WorkspaceError
from agent_builder.core.state import Plan, PlanTask
from agent_builder.core.workspace import Workspace
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage
from agent_builder.tools.file_ops import read_project_file, write_project_files

CODER_SYSTEM = """You are the Coder agent for Agent Team Builder.
Output source files using markdown code fences with filenames.
For edits to existing files, use SEARCH/REPLACE patch blocks when possible.
Example new file: ```python:main.py
print("hello")
```
No prose outside code fences."""


class CoderAgent(BaseAgent):
    """Writes generated source files into ``workspace/project/``."""

    name = "coder"
    max_retries = 3

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
            return AgentResult(success=False, output="Workspace is required for Coder")

        plan = context.extra.get("plan")
        plan_task: PlanTask | None = context.extra.get("plan_task")
        feedback = str(context.extra.get("feedback", ""))

        files_hint = ""
        if plan_task and plan_task.files_affected:
            files_hint = ", ".join(plan_task.files_affected)
        elif plan_task:
            files_hint = "(infer from task title)"

        design = None
        if self.workspace is not None and plan_task is not None:
            design = load_design_for_task(self.workspace, plan_task.id)

        plan_context = await self._build_plan_context(
            plan,
            plan_task,
            context.user_prompt,
            design=design,
            feedback=feedback,
        )

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

        resolved_files, resolve_errors = self._resolve_code_files(code_files)
        if resolve_errors:
            return AgentResult(
                success=False,
                output="; ".join(resolve_errors),
                data={"raw": response.text, "code_files": code_files},
                last_model=response.model,
            )

        syntax_errors: list[str] = []
        for rel_path, content in resolved_files.items():
            if rel_path.endswith(".py"):
                try:
                    ast.parse(content, filename=rel_path)
                except SyntaxError as exc:
                    syntax_errors.append(f"{rel_path}: {exc}")

        if syntax_errors:
            return AgentResult(
                success=False,
                output="; ".join(syntax_errors),
                data={"raw": response.text, "code_files": code_files},
                last_model=response.model,
            )

        written = write_project_files(self.workspace, resolved_files)

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

    async def _build_plan_context(
        self,
        plan: object,
        task: PlanTask | None,
        user_prompt: str,
        *,
        design: ScreenDesign | None,
        feedback: str,
    ) -> str:
        sections = [_format_plan_context(plan, task)]

        if design is not None:
            sections.append(f"UI design spec:\n{format_design_for_coder(design)}")

        flet_ctx = format_flet_context(task, has_design=design is not None)
        if flet_ctx:
            sections.append(flet_ctx)

        if self.workspace is not None and self.settings.coder_use_index:
            query = build_coder_search_query(user_prompt=user_prompt, plan_task=task)
            hits = await fetch_index_hits(
                self.workspace,
                query,
                settings=self.settings,
            )
            index_ctx = format_index_context(hits)
            if index_ctx:
                sections.append(index_ctx)
            paths = collect_context_paths(task, hits)
            existing_ctx = format_existing_files_context(self.workspace, paths)
            if existing_ctx:
                sections.append(existing_ctx)
        elif self.workspace is not None and task and task.files_affected:
            existing_ctx = format_existing_files_context(
                self.workspace,
                collect_context_paths(task, []),
            )
            if existing_ctx:
                sections.append(existing_ctx)

        if feedback:
            sections.append(f"Previous attempt errors:\n{feedback}")

        return "\n\n".join(section for section in sections if section)

    def _resolve_code_files(self, code_files: list[CodeFile]) -> tuple[dict[str, str], list[str]]:
        """Turn parsed files/patches into final path → content map."""
        assert self.workspace is not None
        resolved: dict[str, str] = {}
        errors: list[str] = []

        for code_file in code_files:
            if code_file.patches:
                try:
                    base = read_project_file(self.workspace, code_file.path)
                except WorkspaceError:
                    base = ""
                try:
                    resolved[code_file.path] = apply_all_patches(
                        base,
                        list(code_file.patches),
                    )
                except PatchApplyError as exc:
                    errors.append(f"{code_file.path}: {exc}")
            else:
                resolved[code_file.path] = code_file.content

        return resolved, errors


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
