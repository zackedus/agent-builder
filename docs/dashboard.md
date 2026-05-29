# Dashboard — Agent Team Builder

**Last updated:** 2026-05-29  
**Package:** `src/agent_builder/dashboard/`  
**Launch:** `agent-builder dashboard` (requires `pip install -e ".[dashboard]"`)

The Flet dashboard is the **primary control plane** for monitoring and operating build sessions. Most CLI workflows can be started from the UI.

---

## Tabs (5)

| # | Tab | Purpose |
|---|-----|---------|
| 0 | **Kontrol** | Run build, resume session, doctor checks, workspace info |
| 1 | **Kanban** | 4-column task board (Menunggu / Sedang dikerjakan / Diblokir / Selesai) |
| 2 | **Dependency** | Sugiyama DAG, filters, zoom/pan, critical path |
| 3 | **Cost** | Metrics, per-agent/model breakdown, trend, budget alerts |
| 4 | **Replay** | Event-sourced timeline scrubber, play/step, bookmarks |

Header also provides: session label, metrics row, live activity feed, dark mode, **⚙ Settings** shortcut.

---

## Tab Kontrol (control plane)

Replaces most day-to-day CLI usage.

| Action | UI | CLI equivalent |
|--------|-----|----------------|
| New build | **Mulai build** | `agent-builder run "prompt"` |
| Resume | **Lanjutkan session** | `agent-builder resume` |
| Environment check | **Refresh cek** | `agent-builder doctor` |
| Terminal fallback | **Terminal** buttons | Same commands in new console (Windows) |

**In-app builds** run the orchestrator via asyncio (`dashboard/services/job_runner.py`). Events publish to the workspace `events.jsonl` and update Kanban/Cost/Replay through `DashboardStore` (poll + live event bus).

**Configuration** still comes from `.env` / environment variables (`AGENT_BUILDER_*`). The dashboard displays current values; permanent changes require editing `.env` and restarting the dashboard.

### Key env vars

| Variable | Effect |
|----------|--------|
| `ANTHROPIC_API_KEY` | Required for builds |
| `AGENT_BUILDER_WORKSPACE` | Workspace root (default `./workspace`) |
| `AGENT_BUILDER_BUDGET_USD` | Budget cap + Cost tab alerts |
| `AGENT_BUILDER_SANDBOX_LAYER` | `auto` / `docker` / `subprocess` |
| `AGENT_BUILDER_LOG_LEVEL` | Logging verbosity |

---

## Replay integration

When the replay slider is not at the live tail:

- **Kanban**, **Dependency**, and **Cost** use reconstructed state from `replay/state_reconstruction.py`.
- Scrubbing the timeline rewinds task status and cumulative cost deterministically.

---

## Module map

```
dashboard/
├── app.py                 # Entry, tabs, poll, replay autoplay
├── theme.py               # Colors, TAB_LABELS
├── flet_ui.py             # Flet 0.85 TabBar/TabBarView helpers
├── state/
│   ├── store.py           # DashboardStore, replay position, job status
│   ├── kanban_tasks.py    # Task status synthesis
│   └── selectors.py       # Header metrics
├── views/
│   ├── control.py         # Tab Kontrol
│   ├── kanban.py
│   ├── dependency_graph.py
│   ├── cost_breakdown.py
│   └── replay.py
├── components/            # Cards, charts, drawers, settings
├── graph/                 # Sugiyama layout
├── cost/                  # Cost aggregation
└── services/
    ├── job_runner.py      # In-app run / resume
    └── doctor.py          # Environment checks
```

---

## Flet 0.85 notes

- Use `ft.Padding` / `ft.Margin`, not `ft.padding` / `ft.margin`.
- Use `Dropdown.on_select`, not `on_change`.
- Canvas lives in `flet.canvas` package.
- Tabs use `TabBar` + `TabBarView` (see `flet_ui.py`).

---

## Not yet in dashboard

- Agent Chat per task (F5.6)
- Edit `.env` from UI
- Keyboard shortcuts / export report (F5.7)

See [PROGRESS.md](../PROGRESS.md) for milestone status.
