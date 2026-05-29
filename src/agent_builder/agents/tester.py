"""Tester agent — static checks, smoke import, pytest in sandbox."""

from __future__ import annotations

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
from agent_builder.agents.test_generator import TestGenerateError, generate_pytest_for_task
from agent_builder.agents.test_models import TesterReport
from agent_builder.agents.test_runner import (
    aggregate_test_status,
    run_pytest,
    run_smoke_import,
)
from agent_builder.core.state import PlanTask
from agent_builder.core.workspace import atomic_write_json
from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox
from agent_builder.tools.static_analysis import run_mypy, run_ruff


class TesterAgent(BaseAgent):
    """Runs automated checks on ``workspace/project/`` for the current task."""

    __test__ = False  # not a pytest test class

    name = "tester"
    max_retries = 1

    async def execute(self, context: AgentContext) -> AgentResult:
        if self.workspace is None:
            return AgentResult(success=False, output="Workspace is required for Tester")

        plan_task: PlanTask | None = context.extra.get("plan_task")
        task_id = context.task_id or (plan_task.id if plan_task else "unknown")
        project_dir = self.workspace.project_dir
        sandbox = SubprocessSandbox(project_dir)

        generated_tests: list[str] = []
        generation_error: str | None = None
        if plan_task is not None:
            try:
                written = await generate_pytest_for_task(
                    self.router,
                    self.workspace,
                    context,
                    plan_task,
                )
                if written is not None:
                    rel = str(written.relative_to(project_dir)).replace("\\", "/")
                    generated_tests.append(rel)
            except TestGenerateError as exc:
                generation_error = str(exc)

        ruff = await run_ruff(project_dir, sandbox)
        mypy = await run_mypy(project_dir, sandbox)
        smoke_status, smoke_out = await run_smoke_import(project_dir, sandbox)
        pytest_run = await run_pytest(project_dir, sandbox)
        pytest_summary = pytest_run.summary

        static_checks = {
            "ruff": ruff.status,
            "mypy": mypy.status,
        }
        status = aggregate_test_status(static_checks, smoke_status, pytest_summary)

        static_output: dict[str, str] = {
            "ruff": ruff.output,
            "mypy": mypy.output,
        }
        if generation_error:
            static_output["test_generation"] = generation_error

        result = TesterReport(
            task_id=task_id,
            status=status,  # type: ignore[arg-type]
            static_checks=static_checks,
            static_output=static_output,
            tests=pytest_summary,
            smoke=smoke_status,
            smoke_output=smoke_out,
            generated_tests=generated_tests,
            coverage=pytest_run.coverage_percent,
        )

        self._save_result(task_id, result)

        summary = _format_summary(result)
        return AgentResult(
            success=False,
            output=summary,
            data={"test_result": result},
        )

    def validate_result(self, result: AgentResult) -> bool:
        test_result = result.data.get("test_result")
        return isinstance(test_result, TesterReport) and test_result.is_passing()

    def _save_result(self, task_id: str, result: TesterReport) -> None:
        assert self.workspace is not None
        path = self.workspace.test_result_path(task_id)
        atomic_write_json(path, result.model_dump(mode="json"))


def _format_summary(result: TesterReport) -> str:
    parts = [
        f"status={result.status}",
        f"ruff={result.static_checks.get('ruff', '?')}",
        f"mypy={result.static_checks.get('mypy', '?')}",
        f"smoke={result.smoke}",
    ]
    if result.generated_tests:
        parts.append(f"generated={','.join(result.generated_tests)}")
    if result.tests.total:
        parts.append(f"pytest={result.tests.passed}/{result.tests.total}")
    if result.coverage is not None:
        parts.append(f"coverage={result.coverage}%")
    if result.tests.failures:
        parts.append(result.tests.failures[0].error[:200])
    return "; ".join(parts)
