# Active Context

**Last updated:** 2026-05-29 — **SESION DISIMPAN** (handoff)

## Lanjut dari sini

- **Phase:** Fase 3 — Milestone **3.4** (E2E self-correction) — **BELUM** dikerjakan
- **Selesai:** Fase 0–2 penuh; Fase 3.1–3.3 (Tester, Reviewer, retry loop)
- **Prompt user berikutnya:** `lanjut` atau *Lanjut F3.4 E2E todo*

## File penting

| Tujuan | Path |
|--------|------|
| Progress & checklist | `PROGRESS.md` §1 |
| Orchestrator FSM | `src/agent_builder/core/orchestrator.py` |
| Tester | `src/agent_builder/agents/tester.py` |
| Reviewer | `src/agent_builder/agents/reviewer.py` |
| Spesifikasi | `ARCHITECTURE.md` |

## Commands cepat

```powershell
cd "g:\baru 2026\april\AI"
.\.venv\Scripts\Activate.ps1
pytest -m "not integration" -q          # harus 129 passed
agent-builder doctor
agent-builder run "Buatkan CLI calculator 2 angka + operasi"  # butuh API key
```

## State repo

- Git: **belum commit**
- venv: `.venv/`
- Tests: 129 passed (non-integration)
