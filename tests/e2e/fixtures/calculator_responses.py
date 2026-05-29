"""Canned LLM responses for calculator E2E (no live API)."""

CALCULATOR_USER_PROMPT = "Buatkan CLI calculator 2 angka + operasi"

CALCULATOR_PLAN_JSON = """
{
  "project_name": "cli_calculator",
  "description": "CLI calculator for two numbers and one operation",
  "tech_stack": {"gui": "none", "storage": null},
  "milestones": [{"id": "M1", "name": "Core", "tasks": ["T1.1"]}],
  "tasks": [
    {
      "id": "T1.1",
      "title": "CLI calculator script",
      "type": "logic",
      "depends_on": [],
      "files_affected": ["calc.py"],
      "acceptance_criteria": [
        "Accepts two numbers and an operator from argv",
        "Prints the numeric result"
      ]
    }
  ],
  "estimated_complexity": "small",
  "risks": ["Division by zero"]
}
"""

CALCULATOR_CODE_RESPONSE = '''
```python:calc.py
"""CLI calculator: python calc.py A OP B"""
import sys

OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
}


def calculate(a: float, op: str, b: float) -> float:
    if op not in OPS:
        raise ValueError(f"Unsupported operator: {op}")
    if op == "/" and b == 0:
        raise ZeroDivisionError("division by zero")
    return OPS[op](a, b)


def _task_args() -> tuple[float, str, float]:
    args = sys.argv[1:]
    if args and args[0] == "--":
        args = args[1:]
    if len(args) != 3:
        print("Usage: python calc.py <a> <op> <b>")
        raise SystemExit(1)
    return float(args[0]), args[1], float(args[2])


def main() -> None:
    a, op, b = _task_args()
    print(calculate(a, op, b))


if __name__ == "__main__":
    main()
```
'''
