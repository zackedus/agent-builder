# Active Context

**Last updated:** 2026-05-29 — F5.2 Kanban view selesai

## Lanjut dari sini

- **Phase:** Fase 5 — **F5.3** Dependency graph (Tab 2)
- **Selesai:** Kanban 4 kolom, task cards, drawer, blocker dialog, `select_task` di store
- **Prompt:** `lanjut` atau *Lanjut F5.3 Dependency graph*

## File penting

| Tujuan | Path |
|--------|------|
| Kanban view | `src/agent_builder/dashboard/views/kanban.py` |
| Task resolution | `src/agent_builder/dashboard/state/kanban_tasks.py` |
| Columns | `src/agent_builder/dashboard/state/kanban_columns.py` |

## Commands

```powershell
pip install -e ".[dashboard]"
agent-builder dashboard
pytest -m "not integration" -q
```
