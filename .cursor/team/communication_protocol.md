# Agent Communication Protocol

## Principle

Agents communicate through written project artifacts.

No agent may rely on hidden memory only.

## Required Communication Artifacts

- Task brief: .cursor/team/tasks/
- Handoff: .cursor/team/handoffs/
- Review report: .cursor/team/reviews/
- Decision record: .cursor/team/decisions/
- Feature registry: .cursor/memory/feature_registry.json
- Module map: docs/module_map.md
- **Dashboard guide (Fase 5+):** [.cursor/team/DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) — team broadcast for all agents

## Dashboard operations (2026-05-29)

Users can run builds from **Tab Kontrol** in `agent-builder dashboard`, not only from CLI.

Agents working on orchestrator, events, Flet UI, or docs must read `DASHBOARD_GUIDE.md` and keep [docs/dashboard.md](../../docs/dashboard.md) accurate after behavior changes.

## Workflow

1. Orchestrator creates task.
2. Assigned agent reads task.
3. Agent inspects relevant code.
4. Agent works only in assigned scope.
5. Agent writes handoff.
6. Next agent reads previous handoff.
7. Reviewer checks output.
8. Documentation agent updates shared docs.

## Standard Flow

New feature:
PM → BA → Logic & Algorithm if needed → Architect → Engineer(s) → QA → Security if needed → Code Reviewer → Docs

Bug fix:
Orchestrator → Relevant Engineer → QA → Code Reviewer → Docs if needed

Database change:
BA → Logic & Algorithm if needed → Architect → Database Engineer → Backend/Integration → QA → Security → Code Reviewer → Docs

Refactor:
Architect → Refactor Engineer → QA → Code Reviewer → Docs

Release:
QA → Security → DevOps → Documentation → Orchestrator

## Conflict Resolution

- Architecture conflict: Solution Architect decides.
- Security conflict: Security Engineer can block.
- Test failure: QA Engineer can block.
- Duplicate implementation: Code Reviewer can block.
- Logic/calculation conflict: Logic & Algorithm Engineer can block.
- Scope conflict: Product Manager decides.
- Final coordination: Orchestrator decides.
