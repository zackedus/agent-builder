# Known Project Patterns

Use this file to store recurring implementation patterns found in the project.

## Dashboard control plane (2026-05-29)

Area: Build / Frontend

Files:
- `src/agent_builder/dashboard/views/control.py`
- `src/agent_builder/dashboard/services/job_runner.py`
- `docs/dashboard.md`

Rules:
- User-facing runs: prefer Tab Kontrol in `agent-builder dashboard`
- In-app jobs use `page.run_task` + `Orchestrator.run_build_pipeline`
- Attach `EventBus` to `DashboardStore` for live feed during in-app builds
- Flet 0.85: `ft.Padding`, `Dropdown.on_select`, `flet.canvas` for graphs

Example usage:
- `agent-builder dashboard` → Kontrol → Mulai build

## Pattern Format

### Pattern name

Area:
Frontend / Backend / Database / API / Auth / Testing / Build / Logic

Files:
- ...

Rules:
- ...

Example usage:
- ...
