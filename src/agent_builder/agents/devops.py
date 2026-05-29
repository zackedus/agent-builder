"""DevOps agent — packaging, build, and release artifacts."""

from __future__ import annotations

from agent_builder.agents.base import AgentContext, AgentResult, BaseAgent
from agent_builder.config import Settings, get_settings
from agent_builder.core.state import Plan
from agent_builder.core.workspace import Workspace
from agent_builder.devops.build_executor import run_pyinstaller_build, smoke_test_executable
from agent_builder.devops.lockfile import generate_requirements_lock
from agent_builder.devops.models import BuildReport
from agent_builder.devops.packager import create_release_package, platform_tag, write_build_report
from agent_builder.devops.spec_builder import generate_pyinstaller_spec
from agent_builder.llm.router import LLMRouter
from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox
from agent_builder.validation.project_output import find_entry_script, find_python_files


class DevOpsAgent(BaseAgent):
    """Packages ``workspace/project/`` into ``workspace/dist/``."""

    name = "devops"
    max_retries = 1

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
            return AgentResult(success=False, output="Workspace is required for DevOps")

        plan: Plan | None = context.extra.get("plan")
        project_name = plan.project_name if plan else "app"

        project_dir = self.workspace.project_dir
        dist_dir = self.workspace.dist_dir
        dist_dir.mkdir(parents=True, exist_ok=True)

        notes: list[str] = []
        report = BuildReport(
            project_name=project_name,
            version="1.0.0",
            platform=platform_tag(),
        )

        req_path = generate_requirements_lock(project_dir)
        report.requirements_path = str(req_path.relative_to(project_dir)).replace("\\", "/")

        py_files = find_python_files(project_dir)
        entry = find_entry_script(project_dir, py_files)
        if entry is not None:
            entry_rel = str(entry.relative_to(project_dir)).replace("\\", "/")
        else:
            entry_rel = "main.py"

        spec_path = generate_pyinstaller_spec(
            project_dir,
            entry_script=entry_rel,
            project_name=project_name,
        )
        report.spec_path = spec_path.name

        sandbox = SubprocessSandbox(project_dir, timeout=300.0)
        build = await run_pyinstaller_build(project_dir, spec_path, sandbox)

        if build.artifact is not None:
            report.artifact_path = str(build.artifact.relative_to(project_dir)).replace("\\", "/")
            smoke_ok, smoke_out = await smoke_test_executable(build.artifact, sandbox)
            report.smoke_ok = smoke_ok
            if smoke_out:
                notes.append(f"smoke: {smoke_out[:120]}")
        elif build.skipped:
            notes.append(build.reason)
        elif build.reason:
            notes.append(build.reason)

        report.notes = notes
        create_release_package(dist_dir, project_dir, report)
        write_build_report(dist_dir, report)

        if build.success and report.smoke_ok:
            report.status = "success"
        elif report.package_path:
            report.status = "partial"
        else:
            report.status = "failed"

        summary = (
            f"status={report.status}; package={report.package_path}; "
            f"checksum={report.checksum_sha256 or 'n/a'}"
        )
        return AgentResult(
            success=False,
            output=summary,
            data={"build_report": report},
        )

    def validate_result(self, result: AgentResult) -> bool:
        report = result.data.get("build_report")
        return isinstance(report, BuildReport) and report.is_acceptable()
