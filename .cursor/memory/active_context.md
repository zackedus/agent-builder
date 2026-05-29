# Active Context

**Last updated:** 2026-05-29 — F4.3 DevOps selesai

## Lanjut dari sini

- **Phase:** Fase 4 — **F4.4** Docker sandbox Layer 2, atau **F4.5** Enhanced Coder
- **Selesai:** DevOps → `dist/*.zip`, `BUILD_REPORT.json`, `orchestrator.execute_deploying()`
- **Prompt:** `lanjut` atau *Lanjut F4.4 Docker*

## File penting

| Tujuan | Path |
|--------|------|
| DevOps agent | `src/agent_builder/agents/devops.py` |
| Lockfile / spec / build | `src/agent_builder/devops/` |
| Orchestrator | `execute_deploying()` di `orchestrator.py` |

## Commands

```powershell
pytest -m "not integration" -q
```
