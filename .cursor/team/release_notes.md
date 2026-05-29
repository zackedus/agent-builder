# Release Notes

## Unreleased

### Added (2026-05-29 — Dashboard control plane)

- **Tab Kontrol** — start build, resume session, doctor checks from dashboard UI
- **5 tabs total:** Kontrol, Kanban, Dependency, Cost, Replay
- In-app build via `dashboard/services/job_runner.py` (live events to activity feed)
- Terminal fallback buttons for full CLI logs
- Header **Settings** dialog (quick run + env summary)
- Team docs: `docs/dashboard.md`, `.cursor/team/DASHBOARD_GUIDE.md`
- All Cursor agents (01–14) notified via roster + `AGENTS.md`

### Changed

- Dashboard is the recommended primary interface (CLI still supported)
- `TAB_LABELS` includes Kontrol as first tab
- Replay scrub rewinds Kanban, Dependency, and Cost views

### Fixed

- Flet 0.85 compatibility: `ft.Padding`, `Dropdown.on_select`, TabBar API

### Risks / Manual Checks

- Edit `.env` still requires file change + dashboard restart
- Long builds block Tab Kontrol job spinner until complete (expected)
- Agent Chat (F5.6) not yet in dashboard
