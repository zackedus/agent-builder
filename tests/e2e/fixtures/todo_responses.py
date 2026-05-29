"""Canned LLM responses for Flet todo + SQLite E2E (no live API)."""

TODO_USER_PROMPT = "Aplikasi Flet todo list dengan SQLite"

TODO_PLAN_JSON = """
{
  "project_name": "flet_todo_sqlite",
  "description": "Flet todo list with SQLite persistence",
  "tech_stack": {"gui": "flet", "storage": "sqlite"},
  "milestones": [{"id": "M1", "name": "Todo core", "tasks": ["T1.1"]}],
  "tasks": [
    {
      "id": "T1.1",
      "title": "Todo app with SQLite backend",
      "type": "ui",
      "depends_on": [],
      "files_affected": ["todo_store.py", "main.py"],
      "acceptance_criteria": [
        "SQLite stores tasks with title and done flag",
        "CRUD: add, mark complete, delete, filter active/done",
        "Flet UI entrypoint without crash on import"
      ]
    }
  ],
  "estimated_complexity": "medium",
  "risks": ["Flet not installed in CI — provide --cli headless mode"]
}
"""

# First attempt: add() forgets commit — list stays empty.
TODO_CODE_V1 = '''
```python:todo_store.py
"""SQLite-backed todo storage."""
from __future__ import annotations

import sqlite3
from pathlib import Path


class TodoStore:
    def __init__(self, db_path: str | Path = "todo.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

    def add(self, title: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, done) VALUES (?, 0)",
                (title,),
            )
            return int(cur.lastrowid or 0)

    def complete(self, task_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE tasks SET done = 1 WHERE id = ?",
                (task_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete(self, task_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cur.rowcount > 0

    def list_tasks(self, *, done: bool | None = None) -> list[tuple[int, str, bool]]:
        query = "SELECT id, title, done FROM tasks"
        params: tuple[object, ...] = ()
        if done is not None:
            query += " WHERE done = ?"
            params = (1 if done else 0,)
        query += " ORDER BY id"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [(int(r[0]), str(r[1]), bool(r[2])) for r in rows]
```

```python:main.py
"""Flet todo app with headless --cli for automated checks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from todo_store import TodoStore

DB_PATH = Path(__file__).resolve().parent / "todo.db"


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Todo CLI (headless)")
    parser.add_argument("--cli", action="store_true", help="Run headless CLI mode")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add")
    add_p.add_argument("title")

    sub.add_parser("list")
    complete_p = sub.add_parser("complete")
    complete_p.add_argument("task_id", type=int)
    delete_p = sub.add_parser("delete")
    delete_p.add_argument("task_id", type=int)

    args = parser.parse_args(argv)
    store = TodoStore(DB_PATH)

    if args.command == "add":
        task_id = store.add(args.title)
        print(f"added:{task_id}")
        return 0
    if args.command == "list":
        for task_id, title, is_done in store.list_tasks():
            status = "done" if is_done else "active"
            print(f"{task_id}|{title}|{status}")
        return 0
    if args.command == "complete":
        ok = store.complete(args.task_id)
        print("ok" if ok else "missing")
        return 0 if ok else 1
    if args.command == "delete":
        ok = store.delete(args.task_id)
        print("ok" if ok else "missing")
        return 0 if ok else 1
    return 1


def launch_flet() -> None:
    import flet as ft

    def main(page: ft.Page) -> None:
        page.title = "Todo"
        page.add(ft.Text("Todo app ready"))

    ft.app(target=main)


if __name__ == "__main__":
    if "--cli" in sys.argv:
        cli_args = sys.argv[sys.argv.index("--cli") + 1 :]
        raise SystemExit(run_cli(cli_args))
    launch_flet()
```
'''

# Second attempt: fixed commit on add; filter flags on list CLI.
TODO_CODE_V2 = '''
```python:todo_store.py
"""SQLite-backed todo storage."""
from __future__ import annotations

import sqlite3
from pathlib import Path


class TodoStore:
    def __init__(self, db_path: str | Path = "todo.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

    def add(self, title: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, done) VALUES (?, 0)",
                (title,),
            )
            conn.commit()
            return int(cur.lastrowid or 0)

    def complete(self, task_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE tasks SET done = 1 WHERE id = ?",
                (task_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete(self, task_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cur.rowcount > 0

    def list_tasks(self, *, done: bool | None = None) -> list[tuple[int, str, bool]]:
        query = "SELECT id, title, done FROM tasks"
        params: tuple[object, ...] = ()
        if done is not None:
            query += " WHERE done = ?"
            params = (1 if done else 0,)
        query += " ORDER BY id"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [(int(r[0]), str(r[1]), bool(r[2])) for r in rows]
```

```python:main.py
"""Flet todo app with headless --cli for automated checks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from todo_store import TodoStore

DB_PATH = Path(__file__).resolve().parent / "todo.db"


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Todo CLI (headless)")
    parser.add_argument("--cli", action="store_true", help="Run headless CLI mode")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add")
    add_p.add_argument("title")

    list_p = sub.add_parser("list")
    list_p.add_argument(
        "--filter",
        choices=("active", "done"),
        default=None,
        help="Filter tasks by status",
    )

    complete_p = sub.add_parser("complete")
    complete_p.add_argument("task_id", type=int)
    delete_p = sub.add_parser("delete")
    delete_p.add_argument("task_id", type=int)

    args = parser.parse_args(argv)
    store = TodoStore(DB_PATH)

    if args.command == "add":
        task_id = store.add(args.title)
        print(f"added:{task_id}")
        return 0
    if args.command == "list":
        done_filter: bool | None = None
        if getattr(args, "filter", None) == "active":
            done_filter = False
        elif getattr(args, "filter", None) == "done":
            done_filter = True
        for task_id, title, is_done in store.list_tasks(done=done_filter):
            status = "done" if is_done else "active"
            print(f"{task_id}|{title}|{status}")
        return 0
    if args.command == "complete":
        ok = store.complete(args.task_id)
        print("ok" if ok else "missing")
        return 0 if ok else 1
    if args.command == "delete":
        ok = store.delete(args.task_id)
        print("ok" if ok else "missing")
        return 0 if ok else 1
    return 1


def launch_flet() -> None:
    import flet as ft

    def main(page: ft.Page) -> None:
        page.title = "Todo"
        page.add(ft.Text("Todo app ready"))

    ft.app(target=main)


if __name__ == "__main__":
    if "--cli" in sys.argv:
        cli_args = sys.argv[sys.argv.index("--cli") + 1 :]
        raise SystemExit(run_cli(cli_args))
    launch_flet()
```
'''
