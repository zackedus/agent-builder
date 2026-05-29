# Active Context

**Last updated:** 2026-05-29 — F4.4 Docker sandbox selesai

## Lanjut dari sini

- **Phase:** Fase 4 — **F4.5** Enhanced Coder (Indexer context), atau **F4.6** E2E validation
- **Selesai:** Docker Layer 2 + fallback Layer 1 via `create_project_sandbox()`
- **Prompt:** `lanjut` atau *Lanjut F4.5 Coder*

## File penting

| Tujuan | Path |
|--------|------|
| Docker sandbox | `src/agent_builder/sandbox/docker_sandbox.py` |
| Factory / fallback | `src/agent_builder/sandbox/factory.py` |
| Env | `AGENT_BUILDER_SANDBOX_LAYER=auto` |

## Commands

```powershell
pytest -m "not integration" -q
docker build -t agent-builder-sandbox:3.11 -f src/agent_builder/sandbox/images/Dockerfile src/agent_builder/sandbox/images
```
