# Team Broadcast — Dashboard Control Plane (2026-05-29)

> **All Cursor agents (00–14):** Read this when working on Fase 5, Flet UI, workspace visibility, or user-facing operations.

## What changed

The **Agent Team Builder dashboard** is no longer view-only. Users can operate builds from **Tab Kontrol** inside `agent-builder dashboard`.

**Authoritative docs:** [docs/dashboard.md](../../docs/dashboard.md)

## Five tabs

1. **Kontrol** — run, resume, doctor (replaces most CLI for users)
2. **Kanban** — task board + detail drawer + blocker dialog
3. **Dependency** — interactive DAG (Sugiyama + canvas)
4. **Cost** — spend breakdown + budget 50/80/100% alerts
5. **Replay** — scrub timeline; Kanban/Cost rewind with event sourcing

## Implications per role

| Agent | Action |
|-------|--------|
| **00 Orchestrator** | Point users to Tab Kontrol; ensure handoffs mention dashboard when UI-relevant |
| **01 PM / 02 BA** | Acceptance criteria may include “visible on Kanban” / status labels |
| **03 Architect** | Events must remain persistable to `events.jsonl` for replay |
| **04 Frontend** | Flet 0.85 API; follow `dashboard/flet_ui.py` patterns |
| **05 Backend** | Orchestrator events drive dashboard; avoid breaking `EventType` payloads |
| **07 Integration** | `DashboardStore.refresh()` polls workspace every 2s |
| **08 QA** | Test dashboard + in-app build path; `pytest -m "not integration"` |
| **10 DevOps** | Build output still under `workspace/project/`; dashboard does not replace packaging |
| **11 Code Reviewer** | Dashboard changes live under `src/agent_builder/dashboard/` |
| **13 Documentation** | Keep `docs/dashboard.md`, README, module_map in sync |
| **14 Logic** | Replay reconstruction must match orchestrator state semantics |

## Runtime vs Cursor agents

| System | Count | Location |
|--------|-------|----------|
| **Runtime agents** (Planner, Coder, …) | 7 | `src/agent_builder/agents/` — power the build pipeline |
| **Cursor workflow agents** | 15 | `.cursor/agents/` — how we develop this repo |

Do not confuse the two. The dashboard monitors **runtime** pipeline state.

## Commands (still valid)

```powershell
pip install -e ".[dashboard]"
agent-builder dashboard
agent-builder run "..."      # also available in Tab Kontrol
agent-builder resume         # also in Tab Kontrol
agent-builder doctor         # also in Tab Kontrol
```

## When updating dashboard code

1. Read `docs/dashboard.md` and `active_context.md`.
2. Run `pytest -m "not integration"` and launch dashboard once on Flet 0.85+.
3. Update `docs/module_map.md` if modules move.
4. Append session log in `PROGRESS.md` for milestone work.

## Open milestones

- **F5.6** Agent Chat drawer
- **F5.7** Polish (shortcuts, toasts, export)

---

*This file is the team-wide broadcast. Do not duplicate long specs in individual agent files—link here instead.*
