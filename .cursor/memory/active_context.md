# Active Context

**Last updated:** 2026-05-29 — F5.3 Dependency graph selesai

## Lanjut dari sini

- **Phase:** Fase 5 — **F5.4** Cost breakdown (Tab 3)
- **Selesai:** Sugiyama layout, `flet.canvas` edges, filter status/agent, zoom/pan, klik node
- **Prompt:** `lanjut` atau *Lanjut F5.4 Cost breakdown*

## File penting

| Tujuan | Path |
|--------|------|
| Graph view | `src/agent_builder/dashboard/views/dependency_graph.py` |
| Layout | `src/agent_builder/dashboard/graph/sugiyama_layout.py` |
| Canvas | `src/agent_builder/dashboard/components/dependency_graph_canvas.py` |

## Commands

```powershell
pip install -e ".[dashboard]"
agent-builder dashboard
pytest -m "not integration" -q
```
