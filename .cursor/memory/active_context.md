# Active Context

**Last updated:** 2026-05-29 — F5.4 Cost breakdown selesai

## Lanjut dari sini

- **Phase:** Fase 5 — **F5.5** Replay (Tab 4)
- **Selesai:** metrics, bar agent, model breakdown, trend canvas, token table, budget alerts + pause
- **Prompt:** `lanjut` atau *Lanjut F5.5 Replay*

## File penting

| Tujuan | Path |
|--------|------|
| Cost view | `src/agent_builder/dashboard/views/cost_breakdown.py` |
| Aggregates | `src/agent_builder/dashboard/cost/aggregates.py` |
| Budget | `src/agent_builder/llm/budget.py` |

## Commands

```powershell
$env:AGENT_BUILDER_BUDGET_USD="10"
agent-builder dashboard
pytest -m "not integration" -q
```
