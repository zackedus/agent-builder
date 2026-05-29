"""Validate generated Python projects under ``workspace/project/``."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from agent_builder.core.event_bus import Event, EventType
from agent_builder.core.state import SessionMetrics, SessionState
from agent_builder.llm.cost_tracker import estimate_cost

if TYPE_CHECKING:
    from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox

ENTRY_CANDIDATES = ("calc.py", "main.py", "app.py", "cli.py", "run.py")


def _needs_argv_separator(args: list[str]) -> bool:
    """Windows CPython treats leading ``+``/``-`` tokens as interpreter flags."""
    if sys.platform != "win32":
        return False
    return any(arg.startswith(("+", "-")) and arg not in ("-", "--") for arg in args)


def _python_script_command(script: Path, args: list[str]) -> list[str]:
    command = [sys.executable, str(script.resolve())]
    if _needs_argv_separator(args):
        command.append("--")
    command.extend(args)
    return command


@dataclass
class ProjectValidationResult:
    """Outcome of syntax and optional runtime checks."""

    python_files: list[str] = field(default_factory=list)
    syntax_errors: list[str] = field(default_factory=list)
    entry_script: str | None = None
    run_exit_code: int | None = None
    run_stdout: str = ""
    run_stderr: str = ""
    run_blocked: bool = False
    run_block_reason: str | None = None

    @property
    def syntax_ok(self) -> bool:
        return not self.syntax_errors and bool(self.python_files)

    @property
    def run_ok(self) -> bool:
        if self.run_blocked:
            return False
        return self.run_exit_code == 0


@dataclass(frozen=True)
class BuildMetricsSummary:
    total_llm_calls: int
    total_cost_usd: float
    elapsed_seconds: int
    input_tokens: int
    output_tokens: int


def find_python_files(project_dir: Path) -> list[Path]:
    """List ``.py`` files under *project_dir* (sorted, stable)."""
    if not project_dir.is_dir():
        return []
    return sorted(
        path
        for path in project_dir.rglob("*.py")
        if path.is_file() and "__pycache__" not in path.parts
    )


def validate_python_syntax(paths: list[Path]) -> list[str]:
    """Return syntax error messages (empty if all files parse)."""
    errors: list[str] = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path.name}: {exc}")
        except OSError as exc:
            errors.append(f"{path.name}: {exc}")
    return errors


def find_entry_script(project_dir: Path, python_files: list[Path]) -> Path | None:
    """Pick a likely CLI entry script."""
    by_name = {p.name: p for p in python_files}
    for name in ENTRY_CANDIDATES:
        if name in by_name:
            return by_name[name]

    for path in python_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, OSError):
            continue
        for node in tree.body:
            if isinstance(node, ast.If) and _is_main_guard(node.test):
                return path
    return python_files[0] if python_files else None


def _is_main_guard(test: ast.expr) -> bool:
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    left = test.left
    right = test.comparators[0] if test.comparators else None
    return (
        isinstance(left, ast.Name)
        and left.id == "__name__"
        and isinstance(right, ast.Constant)
        and right.value == "__main__"
    )


async def run_entry_script(
    sandbox: SubprocessSandbox,
    script: Path,
    args: list[str],
    *,
    cwd: Path | None = None,
) -> tuple[int | None, str, str, bool, str | None]:
    """Run ``python script args…`` and return exit code and streams."""
    command = _python_script_command(script, args)
    result = await sandbox.run_command(command, cwd=cwd or script.parent)
    return (
        result.returncode,
        result.stdout,
        result.stderr,
        result.blocked,
        result.block_reason,
    )


async def validate_project_output(
    project_dir: Path,
    *,
    run_args: list[str] | None = None,
    sandbox: SubprocessSandbox | None = None,
) -> ProjectValidationResult:
    from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox as _Sandbox

    """Check Python files exist, parse, and optionally execute the entry script."""
    python_files = find_python_files(project_dir)
    rel_paths = [str(p.relative_to(project_dir)).replace("\\", "/") for p in python_files]
    syntax_errors = validate_python_syntax(python_files)
    entry = find_entry_script(project_dir, python_files)
    entry_rel = (
        str(entry.relative_to(project_dir)).replace("\\", "/") if entry is not None else None
    )

    outcome = ProjectValidationResult(
        python_files=rel_paths,
        syntax_errors=syntax_errors,
        entry_script=entry_rel,
    )

    if run_args is None or entry is None or syntax_errors:
        return outcome

    sb = sandbox or _Sandbox(project_dir)
    code, stdout, stderr, blocked, reason = await run_entry_script(
        sb,
        entry,
        run_args,
        cwd=project_dir,
    )
    outcome.run_exit_code = code
    outcome.run_stdout = stdout
    outcome.run_stderr = stderr
    outcome.run_blocked = blocked
    outcome.run_block_reason = reason
    return outcome


SELF_CORRECTION_EVENTS = frozenset({"tests_fail", "changes_requested"})


def count_self_corrections(events: list[Event]) -> int:
    """Count TESTING/REVIEWING → CODING retry transitions in persisted events."""
    count = 0
    for event in events:
        if event.type != EventType.STATE_CHANGED:
            continue
        if event.payload.get("event") not in SELF_CORRECTION_EVENTS:
            continue
        from_state = event.payload.get("from")
        to_state = event.payload.get("to")
        if from_state in ("TESTING", "REVIEWING") and to_state == "CODING":
            count += 1
    return count


def assert_flet_entrypoint(project_dir: Path, *, entry_name: str = "main.py") -> None:
    """Assert the Flet entry script parses and references ``flet`` (no GUI launch)."""
    entry = project_dir / entry_name
    if not entry.is_file():
        raise AssertionError(f"Missing entry script: {entry_name}")
    source = entry.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(entry))
    if "flet" not in source and "ft" not in source:
        raise AssertionError(f"{entry_name} does not reference Flet")
    has_launch = any(
        isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Attribute) and node.func.attr == "app")
            or (isinstance(node.func, ast.Name) and node.func.id == "app")
        )
        for node in ast.walk(tree)
    )
    if not has_launch:
        raise AssertionError(f"{entry_name} has no ft.app() launch call")


@dataclass
class TodoCrudValidation:
    """Outcome of headless todo CRUD checks via ``main.py --cli``."""

    steps_ok: bool = True
    errors: list[str] = field(default_factory=list)


async def validate_todo_crud(
    project_dir: Path,
    *,
    sandbox: SubprocessSandbox | None = None,
) -> TodoCrudValidation:
    """Run add/list/complete/filter/delete against generated todo project."""
    from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox as _Sandbox

    entry = project_dir / "main.py"
    outcome = TodoCrudValidation()
    if not entry.is_file():
        outcome.steps_ok = False
        outcome.errors.append("main.py not found")
        return outcome

    db_path = project_dir / "todo.db"
    if db_path.is_file():
        db_path.unlink()

    sb = sandbox or _Sandbox(project_dir)

    async def run_step(
        args: list[str],
        *,
        expect_in_stdout: str | None = None,
        must_not_contain: str | None = None,
    ) -> str:
        code, stdout, stderr, blocked, reason = await run_entry_script(sb, entry, ["--cli", *args])
        if blocked:
            outcome.steps_ok = False
            outcome.errors.append(f"blocked {args}: {reason}")
            return stdout
        if code != 0:
            outcome.steps_ok = False
            outcome.errors.append(f"exit {code} for {args}: {stderr or stdout}")
            return stdout
        if expect_in_stdout and expect_in_stdout not in stdout:
            outcome.steps_ok = False
            outcome.errors.append(
                f"expected {expect_in_stdout!r} in stdout for {args}, got {stdout!r}"
            )
        if must_not_contain and must_not_contain in stdout:
            outcome.steps_ok = False
            outcome.errors.append(
                f"did not expect {must_not_contain!r} in stdout for {args}, got {stdout!r}"
            )
        return stdout

    await run_step(["add", "Buy milk"], expect_in_stdout="added:")
    await run_step(["list"], expect_in_stdout="Buy milk")
    await run_step(["complete", "1"], expect_in_stdout="ok")
    await run_step(["list", "--filter", "done"], expect_in_stdout="Buy milk")
    await run_step(["list", "--filter", "active"], must_not_contain="Buy milk")
    await run_step(["delete", "1"], expect_in_stdout="ok")
    await run_step(["list"], must_not_contain="Buy milk")
    return outcome


@dataclass
class ExpenseValidation:
    """Outcome of headless expense tracker CLI checks."""

    steps_ok: bool = True
    errors: list[str] = field(default_factory=list)


async def validate_expense_features(
    project_dir: Path,
    *,
    month: str | None = None,
    sandbox: SubprocessSandbox | None = None,
) -> ExpenseValidation:
    """Run add/list/summary/chart checks via ``main.py --cli``."""
    from datetime import date

    from agent_builder.sandbox.subprocess_sandbox import SubprocessSandbox as _Sandbox

    entry = project_dir / "main.py"
    outcome = ExpenseValidation()
    if not entry.is_file():
        outcome.steps_ok = False
        outcome.errors.append("main.py not found")
        return outcome

    if not (project_dir / "expense_store.py").is_file():
        outcome.steps_ok = False
        outcome.errors.append("expense_store.py not found")
        return outcome

    if not (project_dir / "chart_data.py").is_file():
        outcome.steps_ok = False
        outcome.errors.append("chart_data.py not found")
        return outcome

    db_path = project_dir / "expenses.db"
    if db_path.is_file():
        db_path.unlink()

    resolved_month = month or date.today().strftime("%Y-%m")
    sb = sandbox or _Sandbox(project_dir)

    async def run_step(
        args: list[str],
        *,
        expect_in_stdout: str | None = None,
    ) -> str:
        code, stdout, stderr, blocked, reason = await run_entry_script(sb, entry, ["--cli", *args])
        if blocked:
            outcome.steps_ok = False
            outcome.errors.append(f"blocked {args}: {reason}")
            return stdout
        if code != 0:
            outcome.steps_ok = False
            outcome.errors.append(f"exit {code} for {args}: {stderr or stdout}")
            return stdout
        if expect_in_stdout and expect_in_stdout not in stdout:
            outcome.steps_ok = False
            outcome.errors.append(
                f"expected {expect_in_stdout!r} in stdout for {args}, got {stdout!r}"
            )
        return stdout

    await run_step(["add", "100000", "Makan"], expect_in_stdout="added:")
    await run_step(["add", "50000", "Transport"], expect_in_stdout="added:")
    await run_step(["list"], expect_in_stdout="Makan")
    await run_step(
        ["summary", "--month", resolved_month],
        expect_in_stdout="CHART:Makan:100000.00",
    )
    await run_step(
        ["summary", "--month", resolved_month],
        expect_in_stdout="CHART:Transport:50000.00",
    )
    await run_step(
        ["summary", "--month", resolved_month],
        expect_in_stdout="TOTAL:150000.00",
    )
    return outcome


def assert_calculator_output(stdout: str, expected: float, *, tolerance: float = 1e-6) -> None:
    """Assert *stdout* contains a numeric result close to *expected*."""
    tokens = stdout.replace(",", " ").split()
    numbers: list[float] = []
    for token in tokens:
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    if not numbers:
        raise AssertionError(f"No numeric output in stdout: {stdout!r}")
    if not any(abs(n - expected) <= tolerance for n in numbers):
        raise AssertionError(
            f"Expected ~{expected} in output, got numbers {numbers} from: {stdout!r}"
        )


def summarize_metrics_from_events(
    events: list[Event],
    session: SessionState,
) -> BuildMetricsSummary:
    """Aggregate LLM usage and elapsed time for a build session."""
    llm_events = [e for e in events if e.type == EventType.LLM_CALL]
    input_tokens = 0
    output_tokens = 0
    total_cost = 0.0
    for event in llm_events:
        inp = int(event.payload.get("input_tokens", 0))
        out = int(event.payload.get("output_tokens", 0))
        model = str(event.payload.get("model", "ollama"))
        input_tokens += inp
        output_tokens += out
        total_cost += estimate_cost(model, inp, out)

    started = session.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    elapsed = int((datetime.now(UTC) - started).total_seconds())

    return BuildMetricsSummary(
        total_llm_calls=len(llm_events),
        total_cost_usd=total_cost,
        elapsed_seconds=max(elapsed, 0),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def apply_metrics_to_session(session: SessionState, summary: BuildMetricsSummary) -> SessionState:
    """Update persisted session metrics from a build summary."""
    session.metrics = SessionMetrics(
        total_llm_calls=summary.total_llm_calls,
        total_cost_usd=summary.total_cost_usd,
        elapsed_seconds=summary.elapsed_seconds,
    )
    return session
