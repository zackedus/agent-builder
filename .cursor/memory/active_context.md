# Active Context

**Last updated:** 2026-05-29 — F4.5 Enhanced Coder selesai

## Lanjut dari sini

- **Phase:** Fase 4 — **F4.6** E2E validation (expense tracker → .exe)
- **Selesai:** Coder + Indexer context, SEARCH/REPLACE patches, Flet reference
- **Prompt:** `lanjut` atau *Lanjut F4.6 E2E*

## File penting

| Tujuan | Path |
|--------|------|
| Coder context | `src/agent_builder/agents/coder_context.py` |
| Patches | `src/agent_builder/agents/code_patches.py` |
| Env | `AGENT_BUILDER_CODER_USE_INDEX=true` |

## Commands

```powershell
pytest -m "not integration" -q
```
