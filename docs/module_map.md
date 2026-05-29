# Module Map

**Last scan:** 2026-05-29 (Sprint #0 complete)

## Project Type

| Field | Value |
|---|---|
| **Repository role** | Cursor AI Developer Team template + **Agent Team Builder** architecture/spec (pre-implementation) |
| **Language** | Python 3.11+ (`src/agent_builder/`) |
| **Framework (target app)** | Flet (GUI for generated apps + dashboard) |
| **Runtime** | CPython 3.11+ |
| **Package manager** | `pip` + `pyproject.toml` |
| **Database** | SQLite (typical for generated apps); ChromaDB for code index (planned) |
| **Auth** | N/A (CLI/desktop tool; no auth layer in repo yet) |
| **API style** | N/A (no HTTP API in repo); blackboard via JSON/files (`state.json`, `plan.json`, etc.) |
| **Testing** | pytest, ruff, mypy (planned per `ARCHITECTURE.md` §9, `PROGRESS.md` S0.7–S0.8) |

## Actual vs Planned Layout

### Present today (documentation & Cursor workflow only)

```
AI/
├── AGENTS.md                 # Multi-agent workflow rules (Cursor)
├── ARCHITECTURE.md           # Full spec: Agent Team Builder v1.1
├── PROGRESS.md               # Dev tracking (Fase 0)
├── PROMPTS.md                # Prompts for Agent Team Builder dev sessions
├── README_SETUP.md           # How to use Cursor team template
├── docs/                     # Project knowledge (mostly templates)
├── .cursor/
│   ├── agents/               # 15 role definitions (00–14)
│   ├── rules/                # Cursor rules (*.mdc)
│   ├── memory/               # project_brief, active_context, feature_registry
│   └── team/                 # task board, handoffs, prompts, protocols
└── (no src/, tests/, pyproject.toml yet)
```

### Planned application layout (`ARCHITECTURE.md` §10, §22)

```
agent-team-builder/
├── pyproject.toml
├── src/agent_builder/
│   ├── core/          # orchestrator, workspace, state, event_bus
│   ├── agents/        # planner, indexer, designer, coder, tester, reviewer, devops
│   ├── llm/           # router, claude/ollama clients, prompts
│   ├── sandbox/       # subprocess + docker
│   ├── indexing/      # chroma, chunker
│   ├── dashboard/     # Flet UI (Fase 5)
│   └── replay/
└── tests/
```

## Build / Lint / Test Commands

| Command | Status | Notes |
|---|---|---|
| `pip install -e ".[dev]"` | Ready | Sprint S0 |
| `pytest` | Ready | 5 unit tests |
| `ruff check .` | Ready | |
| `mypy src` | Ready | |
| `agent-builder --help` | Ready | |
| `agent-builder doctor` | Ready | Checks API key + Ollama |
| `agent-builder run "..."` | Ready | Starts session → PLANNING |
| `agent-builder resume` | Ready | Load session from workspace |
| `agent-builder status [id]` | Ready | Session table + recent events |

### Module: agent-builder-package

**Purpose:** CLI, config, and future orchestrator/agents runtime.

**Main files:**

- `src/agent_builder/cli.py` — Typer commands (`version`, `doctor`, `run`)
- `src/agent_builder/config.py` — `Settings` from `.env`
- `src/agent_builder/core/state.py` — SessionState, Plan, TaskNode, critical path
- `src/agent_builder/core/workspace.py` — atomic JSON I/O, workspace layout
- `src/agent_builder/core/event_bus.py` — pub/sub, Event, EventType
- `src/agent_builder/core/events_store.py` — append-only `events.jsonl`
- `src/agent_builder/core/logging_setup.py` — loguru per-agent files
- `src/agent_builder/core/orchestrator.py` — FSM, dispatch, resume, walk_happy_path
- `src/agent_builder/llm/claude_client.py` — Anthropic async client
- `src/agent_builder/llm/ollama_client.py` — Ollama async client
- `src/agent_builder/llm/router.py` — hybrid routing + failover
- `src/agent_builder/llm/cost_tracker.py` — token cost via `llm_call` events
- `src/agent_builder/llm/prompt_loader.py` — `llm/prompts/*.txt` templates
- `src/agent_builder/agents/base.py` — `BaseAgent`, retry, validation hook
- `src/agent_builder/sandbox/subprocess_sandbox.py` — Layer 1 execution
- `src/agent_builder/sandbox/static_check.py` — AST pre-flight security
- `src/agent_builder/agents/` — planner, coder, … (Fase 2+)

**Test files:** `test_sandbox.py`, `test_base_agent.py`, … (78 unit tests total); `tests/integration/` (opt-in)

## Architecture Pattern

| Layer | Description |
|---|---|
| **Cursor workflow** | Chain: Orchestrator → PM/BA/Logic → Architect → Engineers → QA → Security → Reviewer → Docs (`AGENTS.md`, `.cursor/team/`) |
| **Runtime system (planned)** | Blackboard + FSM Orchestrator; 7 specialists communicate via shared workspace, not direct calls (`ARCHITECTURE.md` §2–5) |
| **Generated apps (planned)** | Feature-based / layered under `workspace/project/` (screens, db, utils per Planner output) |

## Modules (logical — no code packages yet)

### Module: cursor-team-workflow

**Purpose:** Coordinate Cursor agents via shared artifacts (tasks, handoffs, reviews, memory).

**Main files:**

- `AGENTS.md`
- `.cursor/team/agent_roster.md`, `communication_protocol.md`, `task_board.md`
- `.cursor/team/PROMPTS.md`, `tasks/`, `handoffs/`, `reviews/`, `decisions/`
- `.cursor/agents/*.md` (roles 00–14)
- `.cursor/rules/*.mdc`

**Related modules:** `docs/*`, `.cursor/memory/*`

**Data dependencies:** `feature_registry.json`, `active_context.md`, `project_brief.md`

**Known risks:** Overlap with root `PROMPTS.md` (different audience); rules duplicated across `AGENTS.md` and `.cursor/rules/`.

---

### Module: project-documentation

**Purpose:** Single entry for docs index, standards, API/DB placeholders.

**Main files:**

- `docs/INDEX.md`, `coding_standard.md`, `architecture.md` (template)
- `docs/api_contracts.md`, `database_schema.md`, `known_issues.md` (empty templates)

**Related modules:** `ARCHITECTURE.md` (authoritative for Agent Team Builder), `PROGRESS.md`

**Known risks:** `docs/architecture.md` is empty template; **`ARCHITECTURE.md` at repo root is the real architecture spec** — keep in sync or add pointer.

---

### Module: agent-team-builder-spec

**Purpose:** Specification for autonomous multi-agent Python system that builds Flet desktop apps.

**Main files:**

- `ARCHITECTURE.md` (v1.1)
- `PROGRESS.md`
- `PROMPTS.md` (dev-session prompts for this product)

**Related modules:** Planned `src/agent_builder/*` (not created)

**Runtime agents (7):** Planner, Indexer, UI/UX Designer, Coder, Tester, Reviewer, DevOps

**Integration:** Anthropic API, Ollama, ChromaDB, optional Docker sandbox

**Test files:** None yet (`tests/` planned)

**Known risks:** Confusion with 15 Cursor workflow agents (different system, same repo).

---

### Module: feature-registry (placeholder)

**Purpose:** Track features/modules as they are implemented.

**Main files:** `.cursor/memory/feature_registry.json` (example entry only)

**Related modules:** All future `src/agent_builder` and generated `workspace/project/` code

## Integration Rules

Every new feature must document:

- owner module
- related modules
- data source
- route/API impact (if any)
- database impact
- auth/permission impact
- logic/calculation impact
- test impact

## Duplication & Overlap Watchlist

| Item | Risk | Recommendation |
|---|---|---|
| `ARCHITECTURE.md` vs `docs/architecture.md` | Two architecture docs; only root file has content | Point `docs/architecture.md` to root or merge summaries |
| `PROMPTS.md` vs `.cursor/team/PROMPTS.md` | Different scopes (product dev vs generic team workflow) | Keep both; label clearly in `docs/INDEX.md` |
| 7 runtime agents vs 15 Cursor agents | Naming/role confusion | Document mapping in `active_context.md` (done) |
| `AGENTS.md` vs `.cursor/rules/00-ai-team-core.mdc` | Repeated non-negotiable rules | Acceptable; rules file is Cursor-enforced subset |
| Future `src/agent_builder/agents/` vs `.cursor/agents/` | Path/name collision | Use distinct names: runtime `planner.py` vs Cursor `03-solution-architect.md` |
