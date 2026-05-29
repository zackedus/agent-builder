"""LLM-backed pytest generation from plan task acceptance criteria."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from agent_builder.agents.base import AgentContext
from agent_builder.agents.code_parser import CodeParseError, extract_code_files
from agent_builder.core.state import PlanTask
from agent_builder.core.workspace import Workspace
from agent_builder.llm.exceptions import LLMError
from agent_builder.llm.prompt_loader import load_and_render
from agent_builder.llm.router import LLMRouter
from agent_builder.llm.types import LLMMessage, RouteRequest
from agent_builder.tools.file_ops import read_project_file, write_project_file
from agent_builder.validation.project_output import find_python_files

_TESTER_SYSTEM = """You are the Tester agent for Agent Team Builder.
Output a single pytest file using a markdown code fence with the exact path requested.
No prose outside the fence."""


class TestGenerateError(LLMError):
    """Failed to generate pytest from acceptance criteria."""


def task_test_relpath(task_id: str) -> str:
    """Relative path for generated tests for *task_id*."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", task_id).strip("_").lower() or "task"
    return f"tests/test_task_{slug}.py"


def collect_source_context(
    workspace: Workspace,
    plan_task: PlanTask,
    *,
    max_chars: int = 12_000,
) -> str:
    """Read project sources relevant to *plan_task* (truncated)."""
    rel_paths: list[str] = list(plan_task.files_affected)
    if not rel_paths:
        rel_paths = [
            str(p.relative_to(workspace.project_dir)).replace("\\", "/")
            for p in find_python_files(workspace.project_dir)
        ]

    parts: list[str] = []
    total = 0
    for rel in rel_paths:
        if not rel.endswith(".py"):
            continue
        try:
            content = read_project_file(workspace, rel)
        except Exception:
            continue
        chunk = f"### {rel}\n```python\n{content}\n```\n"
        if total + len(chunk) > max_chars:
            parts.append(f"### {rel}\n(truncated — context limit reached)\n")
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n".join(parts) if parts else "(no Python sources found)"


def _validate_test_syntax(content: str, *, filename: str) -> None:
    try:
        ast.parse(content, filename=filename)
    except SyntaxError as exc:
        raise TestGenerateError(f"Generated test has syntax error: {exc}") from exc


async def generate_pytest_for_task(
    router: LLMRouter,
    workspace: Workspace,
    context: AgentContext,
    plan_task: PlanTask,
) -> Path | None:
    """Generate and write pytest for *plan_task*; return path or ``None`` if skipped."""
    if not plan_task.acceptance_criteria:
        return None

    rel_path = task_test_relpath(plan_task.id)
    slug = Path(rel_path).stem.removeprefix("test_task_")
    acceptance = "\n".join(f"- {criterion}" for criterion in plan_task.acceptance_criteria)
    sources = collect_source_context(workspace, plan_task)

    prompt = load_and_render(
        "tester",
        {
            "task_id": plan_task.id,
            "task_title": plan_task.title,
            "user_prompt": context.user_prompt or "—",
            "acceptance_criteria": acceptance,
            "source_files": sources,
            "task_slug": slug,
        },
    )
    messages = [LLMMessage(role="user", content=prompt)]

    response = await router.complete(
        RouteRequest(agent="tester", task_type="default"),
        messages,
        system=_TESTER_SYSTEM,
        max_tokens=4000,
    )

    try:
        code_files = extract_code_files(response.text, default_paths=[rel_path])
    except CodeParseError as exc:
        raise TestGenerateError(str(exc)) from exc

    written: Path | None = None
    for code_file in code_files:
        if not code_file.path.startswith("tests/"):
            continue
        _validate_test_syntax(code_file.content, filename=code_file.path)
        dest = write_project_file(workspace, code_file.path, code_file.content)
        written = dest

    if written is None:
        # Accept exact rel_path even if model used a slightly different tests/ name
        for code_file in code_files:
            if code_file.path.endswith(".py"):
                _validate_test_syntax(code_file.content, filename=code_file.path)
                written = write_project_file(workspace, rel_path, code_file.content)
                break

    if written is None:
        raise TestGenerateError("No pytest file found in model response")

    return written
