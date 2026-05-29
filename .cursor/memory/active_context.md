# Active Context

**Last updated:** 2026-05-29 — F5.1 Dashboard foundation selesai

## Lanjut dari sini

- **Phase:** Fase 5 — **F5.2** Kanban view (4 kolom + task card)
- **Selesai:** `agent-builder dashboard`, 4 tab shell, theme, store, activity feed
- **Prompt:** `lanjut` atau *Lanjut F5.2 Kanban*

## File penting

| Tujuan | Path |
|--------|------|
| Dashboard entry | `src/agent_builder/dashboard/app.py` |
| State store | `src/agent_builder/dashboard/state/store.py` |
| Theme | `src/agent_builder/dashboard/theme.py` |

## Commands

```powershell
pip install -e ".[dashboard]"
agent-builder dashboard
pytest -m "not integration" -q
```
