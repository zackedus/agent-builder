"""Static security analysis before executing generated code."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from agent_builder.sandbox.exceptions import SandboxSecurityError

# Attribute access patterns that are blocked (module, name).
BLOCKED_ATTR_CALLS: frozenset[tuple[str, str]] = frozenset(
    {
        ("os", "system"),
        ("os", "popen"),
        ("os", "spawn"),
        ("os", "execl"),
        ("os", "execle"),
        ("os", "execv"),
        ("subprocess", "call"),
        ("subprocess", "run"),
        ("subprocess", "Popen"),
        ("subprocess", "check_call"),
        ("subprocess", "check_output"),
    }
)

BLOCKED_BUILTINS: frozenset[str] = frozenset({"eval", "exec", "compile", "__import__"})


@dataclass(frozen=True)
class StaticCheckResult:
    issues: list[str]

    @property
    def passed(self) -> bool:
        return not self.issues


class StaticSecurityChecker:
    """AST walker that flags dangerous constructs in Python source."""

    def check(self, code: str, *, filename: str = "<sandbox>") -> StaticCheckResult:
        issues: list[str] = []
        try:
            tree = ast.parse(code, filename=filename)
        except SyntaxError as exc:
            return StaticCheckResult([f"Syntax error: {exc}"])

        for node in ast.walk(tree):
            issues.extend(self._check_node(node))

        return StaticCheckResult(issues)

    def check_or_raise(self, code: str, *, filename: str = "<sandbox>") -> None:
        result = self.check(code, filename=filename)
        if not result.passed:
            raise SandboxSecurityError("; ".join(result.issues))

    def _check_node(self, node: ast.AST) -> list[str]:
        issues: list[str] = []

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_BUILTINS:
                issues.append(f"Blocked builtin call: {node.func.id}()")

            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                pair = (node.func.value.id, node.func.attr)
                if pair in BLOCKED_ATTR_CALLS:
                    issues.append(f"Blocked call: {'.'.join(pair)}()")

        return issues
