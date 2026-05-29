"""Execute pytest and smoke checks in the project sandbox."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from agent_builder.agents.test_models import CheckStatus, TestFailure, TestRunSummary
from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox
from agent_builder.validation.project_output import find_python_files

_PYTEST_FAILURE_RE = re.compile(
    r"^(?P<name>[^\s]+)\s+FAILED",
    re.MULTILINE,
)

COVERAGE_JSON_NAME = ".agent_coverage.json"
COVERAGE_CONFIG_NAME = ".agent_coveragerc"


@dataclass(frozen=True)
class PytestRunResult:
    """Pytest summary plus optional line coverage percentage."""

    summary: TestRunSummary
    coverage_percent: float | None = None


def _pytest_cov_available() -> bool:
    return importlib.util.find_spec("pytest_cov") is not None


def parse_coverage_json(path: Path) -> float | None:
    """Read ``percent_covered`` from a pytest-cov JSON report."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None

    totals = data.get("totals")
    if isinstance(totals, dict):
        percent = totals.get("percent_covered")
        if percent is not None:
            return round(float(percent), 1)

    files = data.get("files")
    if not isinstance(files, dict) or not files:
        return None

    covered = 0
    statements = 0
    for entry in files.values():
        if not isinstance(entry, dict):
            continue
        summary = entry.get("summary", entry)
        if not isinstance(summary, dict):
            continue
        covered += int(summary.get("covered_lines", 0))
        statements += int(summary.get("num_statements", 0))
    if statements == 0:
        return None
    return round(100.0 * covered / statements, 1)


async def run_smoke_import(
    project_dir: Path,
    sandbox: SubprocessSandbox,
) -> tuple[CheckStatus, str]:
    """Compile Python files (lightweight smoke check without executing main)."""
    del sandbox  # compile-only; no subprocess required
    files = find_python_files(project_dir)
    if not files:
        return "skipped", "no Python files"

    errors: list[str] = []
    for path in files[:20]:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (SyntaxError, OSError, ValueError) as exc:
            errors.append(f"{path.name}: {exc}")

    if errors:
        return "failed", "\n".join(errors)
    return "passed", f"compiled {len(files)} file(s)"


async def run_pytest(
    project_dir: Path,
    sandbox: SubprocessSandbox,
    *,
    junit_path: Path | None = None,
    coverage_path: Path | None = None,
) -> PytestRunResult:
    """Run pytest in *project_dir*; parse JUnit XML and optional coverage JSON."""
    tests_dir = project_dir / "tests"
    if not tests_dir.is_dir() and not list(project_dir.glob("test_*.py")):
        return PytestRunResult(summary=TestRunSummary())

    junit = junit_path or project_dir / ".agent_pytest_junit.xml"
    cov_json = coverage_path or project_dir / COVERAGE_JSON_NAME

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        f"--junitxml={junit.name}",
    ]
    coveragerc: Path | None = None
    if _pytest_cov_available():
        coveragerc = project_dir / COVERAGE_CONFIG_NAME
        coveragerc.write_text(
            "[run]\nsource = .\nomit = tests/*\n",
            encoding="utf-8",
        )
        command.extend(
            [
                "--cov=.",
                f"--cov-report=json:{cov_json.name}",
                f"--cov-config={coveragerc.name}",
            ]
        )

    result = await sandbox.run_command(command, cwd=project_dir, timeout=180.0)

    if junit.is_file():
        summary = _parse_junit_xml(junit.read_text(encoding="utf-8"))
        junit.unlink(missing_ok=True)
    else:
        summary = _parse_pytest_text(
            (result.stdout + "\n" + result.stderr).strip(),
            result.returncode,
        )

    coverage_percent: float | None = None
    if cov_json.is_file():
        coverage_percent = parse_coverage_json(cov_json)
        cov_json.unlink(missing_ok=True)
    if coveragerc is not None:
        coveragerc.unlink(missing_ok=True)

    return PytestRunResult(summary=summary, coverage_percent=coverage_percent)


def _parse_junit_xml(xml_text: str) -> TestRunSummary:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return TestRunSummary()

    failures: list[TestFailure] = []
    total = 0
    failed = 0

    for case in root.iter("testcase"):
        total += 1
        failure = case.find("failure")
        error = case.find("error")
        node = failure if failure is not None else error
        if node is not None:
            failed += 1
            name = case.get("name", "unknown")
            classname = case.get("classname", "")
            test_name = f"{classname}.{name}" if classname else name
            failures.append(
                TestFailure(
                    test_name=test_name,
                    error=(node.get("message") or node.text or "failed")[:500],
                    traceback=(node.text or "")[:2000],
                )
            )

    passed = max(total - failed, 0)
    return TestRunSummary(total=total, passed=passed, failed=failed, failures=failures)


def _parse_pytest_text(output: str, returncode: int) -> TestRunSummary:
    if not output and returncode == 0:
        return TestRunSummary()

    failures: list[TestFailure] = []
    for match in _PYTEST_FAILURE_RE.finditer(output):
        failures.append(TestFailure(test_name=match.group("name"), error="FAILED"))

    passed = len(re.findall(r"(\d+) passed", output))
    failed = len(re.findall(r"(\d+) failed", output))
    total = passed + failed
    if total == 0 and returncode != 0 and output:
        failures.append(TestFailure(test_name="pytest", error=output[:500]))
        return TestRunSummary(total=1, passed=0, failed=1, failures=failures)
    return TestRunSummary(
        total=total,
        passed=passed,
        failed=failed,
        failures=failures,
    )


def aggregate_test_status(
    static_checks: dict[str, CheckStatus],
    smoke: CheckStatus,
    tests: TestRunSummary,
) -> str:
    """Return overall ``passed`` | ``failed`` | ``partial``."""
    checks = list(static_checks.values()) + [smoke]
    if tests.total > 0:
        checks.append("passed" if tests.failed == 0 else "failed")

    if all(c in ("passed", "skipped") for c in checks):
        return "passed"
    if any(c == "failed" for c in checks):
        if any(c == "passed" for c in checks):
            return "partial"
        return "failed"
    return "passed"
