"""Canned LLM responses for expense tracker E2E (no live API)."""

EXPENSE_USER_PROMPT = (
    "Buatkan aplikasi pencatat pengeluaran harian dengan grafik bulanan. "
    "Gunakan Flet untuk UI, SQLite untuk penyimpanan, matplotlib untuk chart."
)

EXPENSE_PLAN_JSON = """
{
  "project_name": "expense_tracker",
  "description": "Daily expense tracker with monthly category chart",
  "tech_stack": {"gui": "flet", "storage": "sqlite", "charts": "matplotlib"},
  "milestones": [{"id": "M1", "name": "Expense app", "tasks": ["T1.1"]}],
  "tasks": [
    {
      "id": "T1.1",
      "title": "Expense tracker with SQLite, chart, and Flet UI",
      "type": "ui",
      "depends_on": [],
      "files_affected": ["expense_store.py", "chart_data.py", "main.py"],
      "acceptance_criteria": [
        "SQLite stores amount, category, and date",
        "Monthly chart data per category",
        "Flet entrypoint and headless CLI for add/list/summary"
      ]
    }
  ],
  "estimated_complexity": "medium",
  "risks": ["matplotlib optional in headless CI"]
}
"""

# V1: add() missing commit — summary returns empty totals.
EXPENSE_CODE_V1 = '''
```python:expense_store.py
"""SQLite expense storage."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path


class ExpenseStore:
    def __init__(self, db_path: str | Path = "expenses.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    note TEXT DEFAULT '',
                    spent_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def add(self, amount: float, category: str, *, note: str = "") -> int:
        spent = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO expenses (amount, category, note, spent_at) VALUES (?, ?, ?, ?)",
                (amount, category, note, spent),
            )
            return int(cur.lastrowid or 0)

    def list_expenses(self, *, month: str | None = None) -> list[tuple[int, float, str, str]]:
        query = "SELECT id, amount, category, spent_at FROM expenses"
        params: tuple[object, ...] = ()
        if month:
            query += " WHERE spent_at LIKE ?"
            params = (f"{month}%",)
        query += " ORDER BY id"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [(int(r[0]), float(r[1]), str(r[2]), str(r[3])) for r in rows]

    def monthly_by_category(self, month: str) -> list[tuple[str, float]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT category, SUM(amount) AS total
                FROM expenses
                WHERE spent_at LIKE ?
                GROUP BY category
                ORDER BY category
                """,
                (f"{month}%",),
            ).fetchall()
        return [(str(r[0]), float(r[1])) for r in rows]
```

```python:chart_data.py
"""Format monthly totals for charts and CLI output."""
from __future__ import annotations

from expense_store import ExpenseStore


def format_chart_lines(totals: list[tuple[str, float]]) -> str:
    lines = [f"CHART:{category}:{amount:.2f}" for category, amount in totals]
    return "\\n".join(lines) if lines else "CHART:(empty):0.00"


def build_monthly_chart(store: ExpenseStore, month: str) -> str:
    return format_chart_lines(store.monthly_by_category(month))
```

```python:main.py
"""Flet expense tracker with headless --cli."""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from chart_data import build_monthly_chart
from expense_store import ExpenseStore

DB_PATH = Path(__file__).resolve().parent / "expenses.db"


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expense CLI")
    parser.add_argument("--cli", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add")
    add_p.add_argument("amount", type=float)
    add_p.add_argument("category")
    add_p.add_argument("--note", default="")

    sub.add_parser("list")
    summary_p = sub.add_parser("summary")
    summary_p.add_argument("--month", required=True)

    args = parser.parse_args(argv)
    store = ExpenseStore(DB_PATH)

    if args.command == "add":
        row_id = store.add(args.amount, args.category, note=args.note)
        print(f"added:{row_id}")
        return 0
    if args.command == "list":
        for row_id, amount, category, spent_at in store.list_expenses():
            print(f"{row_id}|{amount:.2f}|{category}|{spent_at}")
        return 0
    if args.command == "summary":
        totals = store.monthly_by_category(args.month)
        total_sum = sum(amount for _, amount in totals)
        print(f"TOTAL:{total_sum:.2f}")
        print(build_monthly_chart(store, args.month))
        return 0
    return 1


def launch_flet() -> None:
    import flet as ft

    def main(page: ft.Page) -> None:
        page.title = "Pengeluaran"
        page.add(ft.Text("Expense tracker ready"))

    ft.app(target=main)


if __name__ == "__main__":
    if "--cli" in sys.argv:
        cli_args = sys.argv[sys.argv.index("--cli") + 1 :]
        raise SystemExit(run_cli(cli_args))
    launch_flet()
```
'''

EXPENSE_CODE_V2 = '''
```python:expense_store.py
"""SQLite expense storage."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path


class ExpenseStore:
    def __init__(self, db_path: str | Path = "expenses.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    note TEXT DEFAULT '',
                    spent_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def add(self, amount: float, category: str, *, note: str = "") -> int:
        spent = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO expenses (amount, category, note, spent_at) VALUES (?, ?, ?, ?)",
                (amount, category, note, spent),
            )
            conn.commit()
            return int(cur.lastrowid or 0)

    def list_expenses(self, *, month: str | None = None) -> list[tuple[int, float, str, str]]:
        query = "SELECT id, amount, category, spent_at FROM expenses"
        params: tuple[object, ...] = ()
        if month:
            query += " WHERE spent_at LIKE ?"
            params = (f"{month}%",)
        query += " ORDER BY id"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [(int(r[0]), float(r[1]), str(r[2]), str(r[3])) for r in rows]

    def monthly_by_category(self, month: str) -> list[tuple[str, float]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT category, SUM(amount) AS total
                FROM expenses
                WHERE spent_at LIKE ?
                GROUP BY category
                ORDER BY category
                """,
                (f"{month}%",),
            ).fetchall()
        return [(str(r[0]), float(r[1])) for r in rows]
```

```python:chart_data.py
"""Format monthly totals for charts and CLI output."""
from __future__ import annotations

from expense_store import ExpenseStore


def format_chart_lines(totals: list[tuple[str, float]]) -> str:
    lines = [f"CHART:{category}:{amount:.2f}" for category, amount in totals]
    return "\\n".join(lines) if lines else "CHART:(empty):0.00"


def build_monthly_chart(store: ExpenseStore, month: str) -> str:
    return format_chart_lines(store.monthly_by_category(month))
```

```python:main.py
"""Flet expense tracker with headless --cli."""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from chart_data import build_monthly_chart
from expense_store import ExpenseStore

DB_PATH = Path(__file__).resolve().parent / "expenses.db"


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expense CLI")
    parser.add_argument("--cli", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add")
    add_p.add_argument("amount", type=float)
    add_p.add_argument("category")
    add_p.add_argument("--note", default="")

    sub.add_parser("list")
    summary_p = sub.add_parser("summary")
    summary_p.add_argument("--month", required=True)

    args = parser.parse_args(argv)
    store = ExpenseStore(DB_PATH)

    if args.command == "add":
        row_id = store.add(args.amount, args.category, note=args.note)
        print(f"added:{row_id}")
        return 0
    if args.command == "list":
        for row_id, amount, category, spent_at in store.list_expenses():
            print(f"{row_id}|{amount:.2f}|{category}|{spent_at}")
        return 0
    if args.command == "summary":
        totals = store.monthly_by_category(args.month)
        total_sum = sum(amount for _, amount in totals)
        print(f"TOTAL:{total_sum:.2f}")
        print(build_monthly_chart(store, args.month))
        return 0
    return 1


def launch_flet() -> None:
    import flet as ft

    def main(page: ft.Page) -> None:
        page.title = "Pengeluaran"
        page.add(ft.Text("Expense tracker ready"))

    ft.app(target=main)


if __name__ == "__main__":
    if "--cli" in sys.argv:
        cli_args = sys.argv[sys.argv.index("--cli") + 1 :]
        raise SystemExit(run_cli(cli_args))
    launch_flet()
```
'''
