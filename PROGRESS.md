# PROGRESS.md — AI Agent Team Builder

**Project:** Agent Team Builder
**Repository:** `agent-team-builder/`
**Architecture spec:** `ARCHITECTURE.md` v1.1
**Last updated:** 2026-05-29
**Current phase:** Fase 4 — Docker sandbox (F4.4 ✅)

---

## Cara Membaca & Update File Ini

> **Untuk Zaki:** File ini adalah single source of truth untuk progress development. Setiap selesai sesi kerja, update bagian "Current Session Log" dan checklist task. Kalau pakai Cursor AI, paste section "Resume Context" di awal sesi baru supaya AI langsung paham state terkini.
>
> **Untuk Cursor AI / LLM:** File ini dirancang untuk dibaca per section. Selalu baca §1 (Resume Context) + §2 (Current Sprint) di awal sesi. Setelah selesai task, update §4 (Task Checklist) dan tambah entry di §5 (Session Log).

**Konvensi status:**
- `[ ]` — Belum dikerjakan
- `[~]` — In progress (lagi dikerjakan, bisa multi-session)
- `[x]` — Selesai
- `[!]` — Blocked / butuh keputusan
- `[s]` — Skipped (dengan alasan)

---

## 1. Resume Context (Baca Pertama!)

> **Section ini di-update setiap akhir sesi.** Tujuannya: kalau buka project lagi setelah seminggu, baca section ini saja sudah cukup paham mau ngerjain apa.

### Status sekarang
- **Phase:** Fase 4 — **F4.4 Docker sandbox** ✅
- **Fase 3:** ✅ selesai (E2E todo + self-correction)
- **Sprint aktif:** F4.5 Enhanced Coder, atau F4.6 E2E validation
- **Task berikutnya:** F4.5.1 Coder + Indexer, F4.1.7 perf test, F4.6 expense tracker E2E
- **Blocker aktif:** —
- **Last commit:** `984a53e` (+ F4.3 belum di-commit sesi ini)
- **Tests:** `pytest -m "not integration"` → **171 passed**

### Ringkasan codebase (apa yang sudah jalan)
| Area | File utama | Status |
|------|------------|--------|
| Planner | `agents/planner.py`, `plan_parser.py` | ✅ |
| Coder | `agents/coder.py`, `code_parser.py`, `tools/file_ops.py` | ✅ |
| Tester | `agents/tester.py`, `agents/test_generator.py`, `test_runner.py` | ✅ (+ LLM pytest gen) |
| Reviewer | `agents/reviewer.py`, `review_parser.py` | ✅ |
| Orchestrator | `core/orchestrator.py` — `run_build_pipeline()`, `execute_*` | ✅ |
| Validasi | `validation/project_output.py` | ✅ |
| CLI | `cli.py` — `run`, `status`, `resume`, `doctor` | ✅ |

### Alur pipeline saat ini
```
run → PLANNING → PLAN_APPROVAL → TASK_LOOP → INDEXING (stub)
  → CODING → TESTING → REVIEWING → (loop task) → INTEGRATION → DEPLOYING → DONE
```
- **TESTS_FAIL** / **CHANGES_REQUESTED** → kembali ke **CODING** (max 3 retry, lalu **FAILED**)
- Coder membaca feedback dari `workspace/.agent/test_results/` dan `reviews/`

### Apa yang harus dilakukan selanjutnya (urutan disarankan)
1. **Fase 4** — Indexer, Designer, DevOps

### Cara lanjut di sesi baru
1. Buka project `g:\baru 2026\april\AI`
2. Aktifkan venv: `.\.venv\Scripts\Activate.ps1`
3. Baca file ini §1 + `.cursor/memory/active_context.md`
4. Di chat Cursor ketik: **`lanjut`** (atau: *"Lanjut F3.4 E2E todo self-correction"*)
5. Opsional cek: `pytest -m "not integration" -q` dan `agent-builder doctor`

### Catatan teknis untuk ingat
- **API:** `ANTHROPIC_API_KEY` di `.env` wajib untuk `run` nyata (Planner + Reviewer pakai LLM)
- **Workspace:** `AGENT_BUILDER_WORKSPACE` (default `./workspace`)
- **Windows:** argumen `+` ke script Python butuh `--` (sudah di `validation/project_output.py`)
- **Model test:** `TesterReport` (bukan `TestResult` — bentrok pytest)
- **Git:** belum commit; user rule — commit hanya kalau diminta

---

## 2. Current Sprint

> **Sprint = unit kerja 1-2 minggu.** Detail per-fase ada di §3.

**Sprint #0 — Setup & Foundation Prep**
**Periode:** 2026-05-29 → 2026-06-01
**Goal:** Repository siap, tooling siap, mulai coding Fase 1.

### Task sprint ini
- [x] **S0.1** Inisialisasi git repository
- [x] **S0.2** Setup `pyproject.toml` dengan dependencies dari §9 ARCHITECTURE.md
- [x] **S0.3** Buat struktur folder sesuai §10 ARCHITECTURE.md
- [x] **S0.4** Buat `.agentrules` untuk Cursor AI
- [x] **S0.5** Buat `PROMPTS.md` (template prompt per use case)
- [x] **S0.6** Setup virtual environment + install deps
- [x] **S0.7** Setup pre-commit hooks (ruff + mypy)
- [x] **S0.8** Setup pytest infrastructure
- [x] **S0.9** Verifikasi Anthropic API key + Ollama installed (`agent-builder doctor`)
- [x] **S0.10** Setup `.env.example` dan config loader

### Definition of Done
- `pip install -e .` berhasil
- `pytest` jalan (walaupun 0 test)
- `ruff check .` clean
- README.md punya "Quick Start" section
- Bisa run `python -m agent_builder --help`

---

## 3. Phase & Milestone Tracking

### Fase 0 — Pre-implementation [x]
**Goal:** Spec dan dokumentasi siap.

- [x] Diskusi arsitektur dengan stakeholder
- [x] `ARCHITECTURE.md` v1.0 (core architecture)
- [x] `ARCHITECTURE.md` v1.1 (+ dashboard spec)
- [x] `PROGRESS.md` (file ini)
- [x] `.agentrules` untuk Cursor AI
- [x] `PROMPTS.md` untuk template prompts
- [x] Repository setup (Sprint #0)

---

### Fase 1 — Foundation [Minggu 1-2] [ ]
**Goal:** Skeleton sistem siap dijalankan, bisa terima prompt tapi belum produktif.
**Reference:** ARCHITECTURE.md §11

#### Milestone 1.1 — Core Models & State [x]
- [x] **F1.1.1** Define `core/state.py` (Pydantic models: SessionState, TaskState, etc.)
- [x] **F1.1.2** Define `core/exceptions.py` (custom exceptions)
- [x] **F1.1.3** Define `core/workspace.py` (path management, atomic write `state.json`)
- [x] **F1.1.4** Unit test untuk state serialization/deserialization
- [x] **F1.1.5** Unit test untuk atomic write (crash safety)

#### Milestone 1.2 — Event Bus & Logging [x]
- [x] **F1.2.1** Implement `core/event_bus.py` (pub/sub in-memory)
- [x] **F1.2.2** Setup loguru dengan per-agent log file
- [x] **F1.2.3** Event sourcing: append ke `events.jsonl`
- [x] **F1.2.4** Unit test event bus subscriber dispatch
- [x] **F1.2.5** Unit test events.jsonl persistence

#### Milestone 1.3 — Orchestrator Skeleton [x]
- [x] **F1.3.1** Implement `core/orchestrator.py` (state machine basic)
- [x] **F1.3.2** Define state enum + transition rules dari §5.2 ARCHITECTURE.md
- [x] **F1.3.3** Persist state setelah setiap transition (atomic write)
- [x] **F1.3.4** Resume from crashed state (load state.json on start)
- [x] **F1.3.5** Integration test: simulate full state cycle (IDLE → DONE)

#### Milestone 1.4 — LLM Router & Clients [x]
- [x] **F1.4.1** Implement `llm/claude_client.py` (Anthropic SDK wrapper)
- [x] **F1.4.2** Implement `llm/ollama_client.py` (ollama Python client)
- [x] **F1.4.3** Implement `llm/router.py` (routing table dari §7.1 ARCHITECTURE.md)
- [x] **F1.4.4** Health check + auto-failover (Ollama down → Claude fallback)
- [x] **F1.4.5** Token counting + cost tracking integration ke event bus
- [x] **F1.4.6** Unit test routing decisions
- [x] **F1.4.7** Integration test (real API call, gated by env var)

#### Milestone 1.5 — Base Agent Class [x]
- [x] **F1.5.1** Implement `agents/base.py` (abstract BaseAgent + retry logic)
- [x] **F1.5.2** Prompt template loader (`llm/prompts/*.txt`)
- [x] **F1.5.3** Result validation interface (each agent override)
- [x] **F1.5.4** Unit test retry budget enforcement (max 3)
- [x] **F1.5.5** Unit test retry escalation (next attempt → stronger model)

#### Milestone 1.6 — Sandbox Layer 1 [x]
- [x] **F1.6.1** Implement `sandbox/base.py` (abstract Sandbox interface)
- [x] **F1.6.2** Implement `sandbox/subprocess_sandbox.py` (cwd, timeout, env whitelist)
- [x] **F1.6.3** Static check pre-execute (block dangerous calls)
- [x] **F1.6.4** Resource limits (Linux: setrlimit; Windows: timeout-only)
- [x] **F1.6.5** Unit test sandbox isolation
- [x] **F1.6.6** Security test (coba escape sandbox)

#### Milestone 1.7 — CLI Entry Point [x]
- [x] **F1.7.1** Implement `cli.py` dengan typer
- [x] **F1.7.2** Command: `agent-builder run <prompt>`
- [x] **F1.7.3** Command: `agent-builder status <session_id>`
- [x] **F1.7.4** Command: `agent-builder resume <session_id>`
- [x] **F1.7.5** Pretty output dengan rich (spinner, tables, panels)
- [x] **F1.7.6** E2E smoke test (run dummy prompt, validate output structure)

**Success criteria Fase 1:**
- CLI bisa dijalankan: `agent-builder run "test prompt"` tidak crash
- State file ter-create di workspace
- Event log tertulis di `events.jsonl`
- Bisa resume dari crashed session
- Test coverage core/ >80%

---

### Fase 2 — Single Agent E2E [Minggu 3] [x]
**Goal:** Planner + Coder bisa generate script Python sederhana.

#### Milestone 2.1 — Planner Agent [x]
- [x] **F2.1.1** Implement `agents/planner.py`
- [x] **F2.1.2** Prompt template (`llm/prompts/planner.txt`)
- [x] **F2.1.3** Validator: output harus parse jadi valid `plan.json` (Pydantic)
- [x] **F2.1.4** Risk identifier (output `risks` array)
- [x] **F2.1.5** Complexity estimator (small/medium/large)
- [x] **F2.1.6** Unit test parsing edge cases (malformed JSON, missing fields)
- [x] **F2.1.7** Integration test dengan real API

#### Milestone 2.2 — Coder Agent (basic) [x]
- [x] **F2.2.1** Implement `agents/coder.py` versi basic (tanpa indexer)
- [x] **F2.2.2** Prompt template (`llm/prompts/coder.txt`)
- [x] **F2.2.3** File operations tool (`tools/file_ops.py`)
- [x] **F2.2.4** Code parser: extract code blocks dari LLM response
- [x] **F2.2.5** Multi-file output handler
- [x] **F2.2.6** Unit test code extraction (markdown fence, multi-block)

#### Milestone 2.3 — Orchestrator Integration [x]
- [x] **F2.3.1** Wire Planner ke state PLANNING
- [x] **F2.3.2** Wire Coder ke state CODING
- [x] **F2.3.3** Task loop: iterate tasks dari plan.json
- [x] **F2.3.4** Pass output Planner sebagai context ke Coder
- [x] **F2.3.5** Mark task done & advance ke next (stub test/review)

#### Milestone 2.4 — E2E Validation [x]
- [x] **F2.4.1** Test prompt: "Buatkan CLI calculator 2 angka + operasi"
- [x] **F2.4.2** Validate output: file Python ada, syntax valid
- [x] **F2.4.3** Validate output: bisa di-run dan output benar
- [x] **F2.4.4** Capture metrics: token usage, cost, duration

**Success criteria Fase 2:**
- Prompt sederhana → 1-3 file Python output
- Output bisa di-jalankan tanpa error syntax
- Cost <$1 per prompt sederhana

---

### Fase 3 — Self-Correction Loop [Minggu 4-5] [~]
**Goal:** Sistem bisa retry otomatis berdasarkan test & review.

#### Milestone 3.1 — Tester Agent [x]
- [x] **F3.1.1** Implement `agents/tester.py`
- [x] **F3.1.2** Static check runner (ruff + mypy)
- [x] **F3.1.3** Pytest generator dari acceptance criteria (LLM)
- [x] **F3.1.4** Smoke test runner (compile check)
- [x] **F3.1.5** Result parser (junit XML + pytest text)
- [x] **F3.1.6** Coverage extraction
- [x] **F3.1.7** Run tests in sandbox (Layer 1)

#### Milestone 3.2 — Reviewer Agent [x]
- [x] **F3.2.1** Implement `agents/reviewer.py`
- [x] **F3.2.2** Prompt template fokus security, anti-pattern, plan adherence
- [x] **F3.2.3** Diff extraction (file content snapshot)
- [x] **F3.2.4** Severity classifier (high/medium/low)
- [x] **F3.2.5** Output validator (review.json schema)

#### Milestone 3.3 — Retry & Loop Logic [x]
- [x] **F3.3.1** State transition: TESTING fail → CODING (retry)
- [x] **F3.3.2** State transition: REVIEWING changes_requested → CODING (retry)
- [x] **F3.3.3** Pass error log + review notes sebagai context retry
- [x] **F3.3.4** Retry counter per task (max 3)
- [x] **F3.3.5** Escalation: switch to stronger model setelah attempt 2 (via BaseAgent)
- [x] **F3.3.6** Final fail → FAILED state

#### Milestone 3.4 — E2E Validation [x]
- [x] **F3.4.1** Test prompt: "Aplikasi Flet todo list dengan SQLite"
- [x] **F3.4.2** Validate: aplikasi launch tanpa crash
- [x] **F3.4.3** Validate: CRUD operations berfungsi
- [x] **F3.4.4** Validate: ada self-correction setidaknya 1x dalam session

**Success criteria Fase 3:**
- Aplikasi medium-complexity bisa di-generate
- Sistem otomatis catch & fix bugs umum
- <10% task butuh manual intervention

---

### Fase 4 — Full Team & Indexing [Minggu 6-7] [ ]
**Goal:** Semua 7 agent aktif, sistem produktif untuk aplikasi medium.

#### Milestone 4.1 — Code Indexer [x]
- [x] **F4.1.1** Implement `indexing/chunker.py` (AST-aware)
- [x] **F4.1.2** Implement `indexing/embedder.py` (Ollama embeddings)
- [x] **F4.1.3** Implement `indexing/chroma_store.py`
- [x] **F4.1.4** Implement `agents/indexer.py`
- [x] **F4.1.5** Auto-trigger re-index on file change (watchdog)
- [x] **F4.1.6** Search API untuk agent lain
- [ ] **F4.1.7** Performance test (codebase 1000 files)

#### Milestone 4.2 — UI/UX Designer [x]
- [x] **F4.2.1** Implement `agents/designer.py`
- [x] **F4.2.2** Prompt template + Flet widget reference
- [x] **F4.2.3** Output validator (design.json schema)
- [x] **F4.2.4** Pass design.json ke Coder sebagai context
- [x] **F4.2.5** Test: form, list, navigation, chart screens

#### Milestone 4.3 — DevOps Agent [x]
- [x] **F4.3.1** Implement `agents/devops.py`
- [x] **F4.3.2** Dependency lock generation (`devops/lockfile.py`)
- [x] **F4.3.3** PyInstaller spec generator (`devops/spec_builder.py`)
- [x] **F4.3.4** Build executor — subprocess Layer 1 (`devops/build_executor.py`); Docker Layer 2 → F4.4
- [x] **F4.3.5** Smoke test executable
- [x] **F4.3.6** Package + checksum + README (`devops/packager.py`, `orchestrator.execute_deploying`)

#### Milestone 4.4 — Sandbox Layer 2 [x]
- [x] **F4.4.1** Implement `sandbox/docker_sandbox.py`
- [x] **F4.4.2** Dockerfile base image (`sandbox/images/Dockerfile`)
- [x] **F4.4.3** Volume mounting strategy (`docker_util.host_mount_path`)
- [x] **F4.4.4** Network isolation (`--network=none`)
- [x] **F4.4.5** Resource limits (`--cpus`, `--memory`)
- [x] **F4.4.6** Auto-cleanup (`docker run --rm`)
- [x] **F4.4.7** Fallback ke Layer 1 (`sandbox/factory.py`, `AGENT_BUILDER_SANDBOX_LAYER`)

#### Milestone 4.5 — Enhanced Coder [ ]
- [ ] **F4.5.1** Upgrade Coder pakai Indexer untuk konteks
- [ ] **F4.5.2** Diff-based editing (bukan full rewrite)
- [ ] **F4.5.3** Multi-file refactor support
- [ ] **F4.5.4** Flet-specific code generation patterns

#### Milestone 4.6 — E2E Validation [ ]
- [ ] **F4.6.1** Test prompt: "Aplikasi pencatat pengeluaran + grafik bulanan"
- [ ] **F4.6.2** Validate: .exe ter-generate
- [ ] **F4.6.3** Validate: .exe bisa di-launch
- [ ] **F4.6.4** Validate: semua fitur berfungsi
- [ ] **F4.6.5** Validate: total cost <$15

**Success criteria Fase 4:**
- Aplikasi medium bisa di-generate end-to-end → .exe
- Total session <45 menit untuk aplikasi medium
- Cost <$15 per session

---

### Fase 5 — Dashboard Full Feature [Minggu 8-10] [ ]
**Goal:** UI dashboard lengkap dengan 4 tab + chat.

#### Milestone 5.1 — Dashboard Foundation [ ]
- [ ] **F5.1.1** Flet app skeleton + routing antar tab
- [ ] **F5.1.2** Theme + color tokens
- [ ] **F5.1.3** Dark mode toggle
- [ ] **F5.1.4** State store (observable, subscribe ke event bus)
- [ ] **F5.1.5** Live activity feed component

#### Milestone 5.2 — Kanban View (Tab 1) [ ]
- [ ] **F5.2.1** 4-column layout
- [ ] **F5.2.2** Task card component
- [ ] **F5.2.3** Agent tag dengan color mapping
- [ ] **F5.2.4** Sub-status indicator (spinner + text)
- [ ] **F5.2.5** Task detail drawer (slide-in dari kanan)
- [ ] **F5.2.6** Blocker resolution dialog

#### Milestone 5.3 — Dependency Graph (Tab 2) [ ]
- [ ] **F5.3.1** Custom Flet canvas component
- [ ] **F5.3.2** Sugiyama layered layout algorithm
- [ ] **F5.3.3** Critical path computation
- [ ] **F5.3.4** Interaksi: click, hover, zoom, pan
- [ ] **F5.3.5** Filter: by status, by agent

#### Milestone 5.4 — Cost Breakdown (Tab 3) [ ]
- [ ] **F5.4.1** Top metrics row
- [ ] **F5.4.2** Bar chart per agent
- [ ] **F5.4.3** Pie chart per model
- [ ] **F5.4.4** Trend line chart over time
- [ ] **F5.4.5** Token usage table
- [ ] **F5.4.6** Budget alerts (50/80/100%)
- [ ] **F5.4.7** Auto-pause on budget exceeded

#### Milestone 5.5 — Replay (Tab 4) [ ]
- [ ] **F5.5.1** Event reader (events.jsonl)
- [ ] **F5.5.2** State reconstruction logic (event sourcing)
- [ ] **F5.5.3** Timeline scrubber
- [ ] **F5.5.4** Play/pause/step controls
- [ ] **F5.5.5** Speed selector (0.5x - 10x)
- [ ] **F5.5.6** Jump to event type (failure, milestone, etc.)
- [ ] **F5.5.7** Auto-bookmark interesting moments

#### Milestone 5.6 — Agent Chat [ ]
- [ ] **F5.6.1** Chat drawer UI
- [ ] **F5.6.2** Context loader (task + agent log)
- [ ] **F5.6.3** Action tag parser
- [ ] **F5.6.4** Action buttons (Apply, Retry, Skip, Switch model)
- [ ] **F5.6.5** Conversation history persistence (optional, per-task)

#### Milestone 5.7 — Polish [ ]
- [ ] **F5.7.1** Keyboard shortcuts (Cmd+P pause, Cmd+R replay, etc.)
- [ ] **F5.7.2** Notification (toast) saat task complete/fail
- [ ] **F5.7.3** Export session report (PDF/HTML)
- [ ] **F5.7.4** Accessibility (keyboard nav, screen reader)
- [ ] **F5.7.5** Performance test (1000+ tasks, smooth UI)

**Success criteria Fase 5:**
- Dashboard responsif (<100ms reaction time)
- Replay 100% akurat (state match dengan live run)
- User testing: 5 task tipikal bisa dilakukan via dashboard

---

## 4. Task Checklist Master (Quick View)

Total milestones per fase:

| Fase | Milestones | Tasks | Status |
|---|---|---|---|
| Fase 0 — Pre-impl | 7 items | 7 | 4/7 done |
| Fase 1 — Foundation | 7 milestones | 38 | 0/38 |
| Fase 2 — Single Agent E2E | 4 milestones | 21 | 0/21 |
| Fase 3 — Self-correction | 4 milestones | 20 | 0/20 |
| Fase 4 — Full Team | 6 milestones | 36 | 0/36 |
| Fase 5 — Dashboard | 7 milestones | 38 | 0/38 |
| **TOTAL** | **35 milestones** | **160 tasks** | **4/160** |

---

## 5. Session Log

> Append-only log per sesi kerja. Format: `## YYYY-MM-DD HH:MM — Topik singkat`

### 2026-05-29 — F4.4 Docker sandbox Layer 2
**Selesai:**
- `docker_sandbox.py`, `docker_util.py`, `sandbox/images/Dockerfile`
- `create_project_sandbox()` + `AGENT_BUILDER_SANDBOX_LAYER=auto|docker|subprocess`
- DevOps memakai Docker saat tersedia; fallback subprocess

**Next:** F4.5 Enhanced Coder

---

### 2026-05-29 — F4.3 DevOps Agent
**Selesai:**
- `devops/` package: lockfile, spec_builder, build_executor, packager, models
- `agents/devops.py`, `orchestrator.execute_deploying()`
- Unit tests: lockfile, spec, packager, agent; E2E pipeline reaches DONE

**Next:** F4.4 Docker sandbox Layer 2

---

### 2026-05-29 — F4.2 UI/UX Designer
**Selesai:**
- `agents/designer.py`, `design_models.py`, `design_parser.py`, `llm/prompts/designer.txt`
- `execute_designing()` di orchestrator; Coder membaca `designs/{task_id}.json`
- Tests: form, list, navigation, chart screen patterns

**Next:** F4.4 Docker sandbox atau F4.5 Enhanced Coder

---

### 2026-05-29 — F4.1.5 Index watcher
**Selesai:**
- `indexing/watcher.py` — `ProjectIndexWatcher` (watchdog)
- Orchestrator: `start_index_watcher` / `stop_index_watcher`, `reindex_files` after Coder
- Tests: `test_index_watcher`, `test_orchestrator_reindex`

**Next:** F4.2 Designer

---

### 2026-05-29 — F4.1 Code Indexer core
**Selesai:**
- `indexing/chunker.py`, `embedder.py`, `chroma_store.py`, `search.py`
- `agents/indexer.py` + `orchestrator.execute_indexing()`
- Unit tests chunker, chroma, indexer

**Next:** F4.1.5 watchdog, F4.2 Designer

---

### 2026-05-29 — F3.1.6 Coverage extraction
**Selesai:**
- `run_pytest()` → `PytestRunResult` dengan `coverage_percent` (pytest-cov JSON)
- `parse_coverage_json()`, temp `.agent_coveragerc` (omit `tests/*`)
- `TesterReport.coverage` terisi; summary CLI menampilkan `coverage=N%`
- `tests/unit/test_coverage.py`

**Next:** Fase 4.1 Indexer

---

### 2026-05-29 — F3.1.3 LLM pytest generator
**Selesai:**
- `agents/test_generator.py` + `llm/prompts/tester.txt`
- `TesterAgent` generates `tests/test_task_{id}.py` before ruff/mypy/pytest
- `TesterReport.generated_tests` field
- Unit tests: `test_test_generator.py`, updated `test_tester_agent.py`

**Next:** F3.1.6 coverage extraction

---

### 2026-05-29 — F3.4 E2E todo + self-correction
**Selesai:**
- `tests/e2e/fixtures/todo_responses.py` — plan + kode V1 (bug commit) / V2 (fix)
- `tests/e2e/test_todo_build.py` — pipeline mocked: test gagal → retry Coder → DONE
- `validation/project_output.py` — `validate_todo_crud`, `assert_flet_entrypoint`, `count_self_corrections`
- **132** tests passed (non-integration)
- Git: initial commit `466addb`, push ke [zackedus/agent-builder](https://github.com/zackedus/agent-builder)

**Next:** F3.1.3 LLM pytest generator

---

### 2026-05-29 (sesi lanjut) — Fase 2 selesai + Fase 3.1–3.3 core
**Durasi:** multi-turn (Cursor)
**Selesai:**
- **Fase 2:** Coder, code parser, file ops, orchestrator task loop, E2E calculator (mocked + validasi)
- **Fase 3:** `TesterAgent` (ruff/mypy/smoke/pytest), `ReviewerAgent` (LLM + review.json)
- Orchestrator: `execute_testing()`, `execute_review()`, retry feedback ke Coder
- `finalize_session_metrics()`, persist `LLM_CALL` ke events.jsonl
- ~129 unit/e2e tests, ruff + mypy clean

**Belum (saat entry ini ditulis):**
- F3.4 E2E todo + self-correction nyata → **selesai di sesi berikutnya**
- F3.1.3 LLM pytest generator, F3.1.6 coverage

---

### 2026-05-29 14:00 — Architecture spec + progress file
**Durasi:** ~2 jam (estimasi)
**Selesai:**
- Diskusi arsitektur (7 agent, Flet stack, hybrid LLM)
- `ARCHITECTURE.md` v1.0 (15 bab, 920 baris)
- Mockup UI dashboard (Kanban style)
- `ARCHITECTURE.md` v1.1 (+ 8 bab dashboard, total 1523 baris)
- `PROGRESS.md` template (file ini)

**Keputusan kunci:**
- Sandbox: hybrid Layer 1 + Layer 2 opt-in
- Real-time: event bus in-memory + file watcher fallback
- Dashboard tech: Flet (bukan Streamlit)
- Roadmap: 10 minggu total (5 fase)
- Dashboard di Fase 5 (setelah core stabil)

**Blocker:**
- Belum decide soal lisensi (MIT vs Apache)
- Belum decide soal multi-user support (v1)

**Next:**
- Bikin `.agentrules` untuk Cursor AI
- Bikin `PROMPTS.md`
- Setup repository (Sprint #0)

---

## 6. Decision Log

> Catat keputusan penting + rationale + tanggal. Berguna saat 6 bulan kemudian lupa kenapa pilih X.

| Tanggal | Keputusan | Rationale | Alternatives considered |
|---|---|---|---|
| 2026-05-29 | GUI dashboard pakai Flet | Konsisten dengan output app, share component | Streamlit (rejected: web-only), Tauri (rejected: butuh JS), PyQt (rejected: kompleks) |
| 2026-05-29 | Real-time via event bus + file watcher | Latency rendah, no networking overhead | WebSocket (rejected: overkill single-process), polling (rejected: laggy) |
| 2026-05-29 | LLM hybrid: Claude API + Ollama | Hemat 75% biaya vs all-Opus | All-Claude (rejected: mahal), all-local (rejected: kualitas rendah untuk reasoning) |
| 2026-05-29 | Sandbox Layer 1 (subprocess) default | Cepat, simple, cukup untuk dev | Docker-only (rejected: butuh Docker installed), no sandbox (rejected: security) |
| 2026-05-29 | Blackboard pattern untuk agent comm | Decoupled, debuggable, mudah test | Direct call (rejected: tight coupling), message queue (rejected: overkill) |
| 2026-05-29 | Custom state machine bukan LangGraph | Lebih ringan, mudah debug | LangGraph (rejected: abstraction tebal di v1) |
| 2026-05-29 | Dashboard di Fase 5 (terakhir) | Backend stabil dulu, baru UI | Dashboard duluan (rejected: tidak ada data untuk ditampilkan) |

---

## 7. Open Questions / Need Decision

> Hal-hal yang harus diputuskan tapi belum ada konsensus. Pindahkan ke Decision Log setelah resolved.

- [ ] **Q1** Lisensi project? (MIT / Apache 2.0 / proprietary)
- [ ] **Q2** Multi-user support di v1 atau v2?
- [ ] **Q3** Storage session history di SQLite atau cukup JSON file?
- [ ] **Q4** Apakah perlu support non-Flet GUI (PyQt) di v1?
- [ ] **Q5** Repository public atau private dulu?
- [ ] **Q6** Budget cap default? ($10? $25? configurable?)
- [ ] **Q7** Auto-update mechanism untuk distributed binary?
- [ ] **Q8** Telemetry / analytics (opt-in) untuk improve product?

---

## 8. Metrics & KPI Targets

> Target measurable per fase. Update saat ada data nyata.

### Fase 2 (Single Agent E2E)
- Cost per simple prompt: <$1 — **Target**
- Generation time: <5 min — **Target**
- Output success rate: >70% — **Target**

### Fase 3 (Self-correction)
- Self-correction rate: >80% bugs caught by Tester — **Target**
- Retry overhead: <30% extra cost — **Target**
- Manual intervention rate: <10% — **Target**

### Fase 4 (Full team)
- Cost per medium prompt: <$15 — **Target**
- Generation time medium app: <45 min — **Target**
- End-to-end success rate: >60% — **Target**

### Fase 5 (Dashboard)
- UI reaction time: <100ms — **Target**
- Replay accuracy: 100% — **Target**
- User satisfaction (internal testing): >4/5 — **Target**

---

## 9. Risk Register (Update saat triggered)

> Refer ARCHITECTURE.md §12 untuk full risk list. Track yang sudah terjadi di sini.

| ID | Risk | Status | Mitigation taken | Date |
|---|---|---|---|---|
| R1 | Infinite retry loop | Not occurred yet | — | — |
| R2 | LLM cost explosion | Not occurred yet | — | — |
| R3 | Generated code merusak host | Not occurred yet | — | — |
| R4 | ChromaDB lambat | Not occurred yet | — | — |
| R5 | Flet API breaking change | Not occurred yet | — | — |

---

## 10. Notes for Future Self

> Catatan random yang relevan tapi tidak masuk section lain.

- **Cursor AI tips:**
  - Baca `.agentrules` dulu sebelum mulai sesi
  - Baca `PROGRESS.md` §1 untuk resume context
  - Saat update progress, commit dengan format `progress: <milestone_id> <description>`

- **Convention:**
  - Branch naming: `phase-N/milestone-MX.X-description` (e.g., `phase-1/milestone-1.3-orchestrator`)
  - Commit prefix: `feat:` (new), `fix:` (bug), `refactor:`, `test:`, `docs:`, `chore:`, `progress:`
  - Task ID di commit message: `feat(F2.2.1): implement coder agent base`

- **Testing strategy:**
  - Unit test: setiap function/class kritikal
  - Integration test: setiap milestone E2E
  - E2E test: setiap fase punya validation prompt

- **Deployment notes (untuk later):**
  - PyInstaller `--onefile` mode untuk distribusi simple
  - Consider Nuitka untuk performance critical
  - Code signing untuk Windows (avoid SmartScreen warning)

---

**End of PROGRESS.md template**

**Cara reset/clone untuk project lain:** Ganti project name di header, kosongkan §5 (Session Log), reset checkbox di §3 (Phase Tracking), kosongkan §6 (Decision Log) kecuali keputusan generik.
