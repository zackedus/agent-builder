"""Tester agent — static checks, smoke import, pytest in sandbox."""

from __future__ import annotations

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
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

        ruff = await run_ruff(project_dir, sandbox)
        mypy = await run_mypy(project_dir, sandbox)
        smoke_status, smoke_out = await run_smoke_import(project_dir, sandbox)
        pytest_summary = await run_pytest(project_dir, sandbox)

        static_checks = {
            "ruff": ruff.status,
            "mypy": mypy.status,
        }
        status = aggregate_test_status(static_checks, smoke_status, pytest_summary)

        result = TesterReport(
            task_id=task_id,
            status=status,  # type: ignore[arg-type]
            static_checks=static_checks,
            static_output={"ruff": ruff.output, "mypy": mypy.output},
            tests=pytest_summary,
            smoke=smoke_status,
            smoke_output=smoke_out,
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
    if result.tests.total:
        parts.append(f"pytest={result.tests.passed}/{result.tests.total}")
    if result.tests.failures:
        parts.append(result.tests.failures[0].error[:200])
    return "; ".join(parts)
