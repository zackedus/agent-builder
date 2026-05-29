# AI Agent Team — Autonomous Application Builder

**Architecture Specification Document**
**Version:** 1.0
**Tanggal:** 29 Mei 2026
**Author:** Zaki (Cirebon, Indonesia)
**Status:** Draft — Pre-Implementation

---

## 1. Ringkasan Eksekutif

### 1.1 Tujuan Sistem

Membangun **multi-agent AI system** berbasis Python yang mampu menerima permintaan natural language dari user (misalnya: *"Buatkan aplikasi pencatat pengeluaran harian dengan grafik bulanan"*) lalu **secara otonom** menghasilkan aplikasi desktop Python (berbasis Flet) yang lengkap, ter-test, ter-review, dan siap di-package menjadi installer/executable.

### 1.2 Karakteristik Kunci

- **Autonomous**: minim intervensi manusia setelah prompt awal
- **Multi-agent collaborative**: 7 agent terspesialisasi dengan tanggung jawab terpisah
- **Self-correcting**: ada retry loop berbasis hasil test & review
- **Hybrid LLM**: kombinasi cloud (Claude API) + lokal (Ollama) untuk efisiensi biaya
- **Observable**: real-time dashboard Kanban-style dengan 4 kolom (Menunggu / Sedang dikerjakan / Diblokir / Selesai), live activity feed, cost tracking, dependency graph, dan session replay
- **Interactive control**: user bisa chat langsung dengan agent tertentu, pause/resume, dan resolve blocker dari dashboard
- **Sandboxed execution**: kode hasil generate dijalankan di environment terisolasi

### 1.3 Output Target

| Aspek | Spesifikasi |
|---|---|
| Bahasa | Python 3.11+ |
| GUI Framework | Flet (Flutter-like, modern) |
| Output Final | Aplikasi `.exe` (Windows) / binary (Linux/macOS) via PyInstaller |
| Source Code | Source Python lengkap + README + tests + dependencies |

---

## 2. Prinsip Desain (Design Principles)

1. **Separation of Concerns** — setiap agent punya 1 tanggung jawab utama. Tidak ada agent yang multitasking.
2. **Blackboard Communication** — agent TIDAK saling memanggil langsung. Semua komunikasi via shared state (`state.json` + filesystem).
3. **Deterministic Orchestration** — yang menentukan urutan eksekusi adalah Orchestrator (state machine), bukan agent. Agent hanya tahu *cara* mengerjakan tugasnya, bukan *kapan*.
4. **Fail Loud, Recover Gracefully** — error tidak boleh disembunyikan. Retry budget terbatas (max 3 attempts per task) lalu eskalasi ke human.
5. **Cost-Aware Routing** — tugas berat reasoning pakai model premium, tugas repetitif pakai model murah/lokal.
6. **Reproducibility** — setiap session bisa di-replay dari log (untuk debugging dan eval).
7. **Human-in-the-Loop Optional** — sistem berjalan otonom tapi user bisa intervene di checkpoint kritikal (misalnya setelah Planning, sebelum Coding mulai).

---

## 3. Arsitektur High-Level

### 3.1 Diagram Arsitektur

```
┌──────────────────────────────────────────────────────────────────┐
│                     USER (CLI / Dashboard UI)                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │  prompt: "Buatkan aplikasi X"
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR                                │
│  - State machine (FSM)                                            │
│  - Task router (siapa kerja sekarang?)                            │
│  - Retry & escalation logic                                       │
│  - LLM router (model selector berdasarkan task)                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
        ┌──────────┬─────────┼─────────┬──────────┬────────┐
        ▼          ▼         ▼         ▼          ▼        ▼
   ┌────────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌────────┐ ┌────────┐
   │Planner │ │Indexer │ │UI/UX │ │Coder │ │Tester  │ │Reviewer│
   └────────┘ └────────┘ └──────┘ └──────┘ └────────┘ └────────┘
                                                          │
                                                          ▼
                                                     ┌────────┐
                                                     │DevOps  │
                                                     └────────┘
        │          │         │         │          │        │
        └──────────┴─────────┴────┬────┴──────────┴────────┘
                                  ▼
              ┌─────────────────────────────────────┐
              │       SHARED WORKSPACE              │
              │  ├── project/        (kode output)  │
              │  ├── state.json      (task state)   │
              │  ├── plan.json       (output Planner)│
              │  ├── design.json     (output UI/UX) │
              │  ├── logs/           (per-agent log)│
              │  └── .vectordb/      (ChromaDB)     │
              └─────────────────────────────────────┘
                                  │
                                  ▼
              ┌─────────────────────────────────────┐
              │  LLM PROVIDERS (via Router)         │
              │  ├── Claude API (Anthropic)         │
              │  └── Ollama (local: qwen2.5-coder)  │
              └─────────────────────────────────────┘
```

### 3.2 Komponen Inti

| Komponen | Tipe | Fungsi Utama |
|---|---|---|
| **Orchestrator** | Service | Mengatur alur eksekusi antar agent |
| **Agent Specialists** | 7 modules | Eksekusi tugas terspesialisasi |
| **Shared Workspace** | Filesystem + JSON + VectorDB | Single source of truth |
| **LLM Router** | Service | Pilih model yang tepat per tugas |
| **Sandbox Executor** | Service | Jalankan kode hasil generate dengan aman |
| **Dashboard** | Web UI (Streamlit) | Monitoring & intervensi user |

---

## 4. Spesifikasi Agent

### 4.1 Planner Agent

**Tanggung jawab:** Menerjemahkan prompt user → rencana eksekusi terstruktur.

**Input:**
- User prompt (string)
- Constraints (opsional: budget, deadline, target platform)

**Output:** `plan.json`
```json
{
  "project_name": "expense_tracker",
  "description": "Aplikasi pencatat pengeluaran dengan grafik bulanan",
  "tech_stack": {
    "gui": "flet",
    "storage": "sqlite",
    "charts": "matplotlib"
  },
  "milestones": [
    {
      "id": "M1",
      "name": "Setup project structure",
      "tasks": ["T1.1", "T1.2"]
    }
  ],
  "tasks": [
    {
      "id": "T1.1",
      "title": "Buat struktur folder dan pyproject.toml",
      "type": "scaffold",
      "depends_on": [],
      "files_affected": ["pyproject.toml", "src/__init__.py"],
      "acceptance_criteria": ["File pyproject.toml valid", "Project dapat di-install dengan pip"]
    }
  ],
  "estimated_complexity": "medium",
  "risks": ["Kompatibilitas Flet dengan PyInstaller"]
}
```

**Model:** Claude Opus 4.7 (reasoning berat)
**Token budget per call:** ~8000 output
**Retry policy:** Max 2 retry jika output bukan JSON valid

---

### 4.2 Code Indexer Agent

**Tanggung jawab:** Membangun & memelihara index semantik dari codebase yang sedang dibangun, sehingga agent lain bisa query "file mana yang relevan untuk task ini?".

**Mengapa penting:** Tanpa indexer, Coder akan sering rewrite file yang sebenarnya hanya perlu diedit, atau lupa konteks yang sudah ada. Ini adalah masalah klasik di Cursor AI yang sering kamu kelola dengan `.cursorrules`.

**Input:**
- Path workspace project
- Trigger: file created/modified

**Output:**
- ChromaDB collection berisi embeddings per code chunk
- API query: `search_relevant_files(query: str, top_k: int) -> List[FileChunk]`

**Tech:**
- Embedding model: `nomic-embed-text` (lokal via Ollama, gratis & cepat)
- Vector DB: ChromaDB (embedded, persisted di `.vectordb/`)
- Chunking strategy: AST-aware (per function/class), bukan per N karakter

**Skema chunk:**
```python
{
  "id": "src/db/models.py::User",
  "file_path": "src/db/models.py",
  "symbol": "User",
  "symbol_type": "class",
  "content": "...",
  "embedding": [...],
  "imports": ["sqlalchemy"],
  "last_modified": "2026-05-29T10:00:00Z"
}
```

**Trigger update:** Setiap kali Coder menyelesaikan task dengan file changes, Orchestrator memanggil Indexer untuk re-index file yang berubah.

---

### 4.3 UI/UX Designer Agent

**Tanggung jawab:** Mengubah deskripsi fitur menjadi spesifikasi UI Flet yang terstruktur.

**Input:**
- Task UI dari Planner (e.g., "Form input pengeluaran dengan kategori dropdown")
- Design system constraints (opsional: brand colors, font)

**Output:** `design.json` (per screen)
```json
{
  "screen_id": "expense_form",
  "title": "Tambah Pengeluaran",
  "layout": "column",
  "widgets": [
    {
      "type": "TextField",
      "id": "amount_input",
      "label": "Nominal (Rp)",
      "input_type": "number",
      "validators": ["required", "positive_number"]
    },
    {
      "type": "Dropdown",
      "id": "category",
      "label": "Kategori",
      "options": ["Makan", "Transport", "Belanja", "Lainnya"]
    },
    {
      "type": "ElevatedButton",
      "id": "submit_btn",
      "label": "Simpan",
      "on_click": "handle_submit"
    }
  ],
  "navigation": {
    "back_to": "home_screen",
    "next_on_success": "home_screen"
  },
  "responsive_breakpoints": {
    "mobile": "<600px",
    "tablet": "600-1024px",
    "desktop": ">1024px"
  }
}
```

**Model:** Claude Sonnet 4.6 (cukup, tidak butuh Opus)
**Catatan khusus Flet:** Designer harus paham widget tree Flet (`ft.Column`, `ft.Row`, `ft.TextField`, dll) — prompt akan menyertakan dokumentasi Flet sebagai konteks.

---

### 4.4 Coder Agent

**Tanggung jawab:** Eksekusi 1 task dari plan → tulis/edit kode di workspace.

**Prinsip:**
- **1 task = 1 file (idealnya)**. Jangan modifikasi banyak file dalam 1 task.
- Selalu **read existing context** (via Indexer query) sebelum tulis.
- Output harus **patch** (diff) bukan full rewrite, kecuali file baru.

**Input:**
- Task object (dari `plan.json`)
- Relevant context (dari Indexer)
- Existing file content (jika edit)
- Design spec (jika task UI)

**Output:**
- File baru / file termodifikasi di workspace
- `task_result.json` dengan status & catatan

**Model routing:**
- Task scaffold/boilerplate → Ollama lokal (`qwen2.5-coder:14b`)
- Task logic kompleks → Claude Sonnet 4.6
- Task arsitektural (refactor besar) → Claude Opus 4.7

**Retry strategy:**
- Attempt 1: prompt dasar
- Attempt 2: tambahkan error log dari attempt 1
- Attempt 3: switch model ke yang lebih kuat
- Setelah 3 fail: eskalasi ke human

---

### 4.5 Tester Agent

**Tanggung jawab:** Generate & jalankan test untuk task yang baru selesai.

**Jenis test:**
1. **Static checks** — `ruff`, `mypy` (otomatis, tanpa LLM)
2. **Unit tests** — pytest, generate dari acceptance criteria
3. **Smoke test** — coba launch aplikasi Flet, cek tidak crash
4. **Integration test** — alur lintas-modul (untuk milestone-level)

**Input:**
- File yang baru di-modify
- Acceptance criteria dari task
- Existing tests (jika ada)

**Output:**
- Test files di `tests/`
- `test_result.json`:
```json
{
  "task_id": "T1.1",
  "status": "passed | failed | partial",
  "static_checks": { "ruff": "passed", "mypy": "passed" },
  "tests": {
    "total": 5,
    "passed": 4,
    "failed": 1,
    "failures": [
      {
        "test_name": "test_negative_amount_rejected",
        "error": "AssertionError: expected ValueError, got None",
        "traceback": "..."
      }
    ]
  },
  "coverage": 78.5
}
```

**Execution:** Sandbox executor (lihat §6)

---

### 4.6 Reviewer Agent

**Tanggung jawab:** Code review semantik (yang tidak bisa di-catch oleh linter).

**Fokus review:**
- Anti-pattern (e.g., bare except, mutable default args)
- Security issues (e.g., SQL injection, hardcoded secrets)
- Code smell (functions terlalu panjang, deep nesting)
- Konsistensi dengan kode existing (naming convention, style)
- Adherence to plan (apakah implementasi sesuai task spec?)

**Input:**
- Diff file yang berubah
- Relevant context (Indexer)
- Project conventions (dari `.agentrules` jika ada)

**Output:** `review.json`
```json
{
  "task_id": "T1.1",
  "verdict": "approved | changes_requested | rejected",
  "issues": [
    {
      "severity": "high | medium | low",
      "type": "security | bug | style | architecture",
      "file": "src/db/models.py",
      "line": 42,
      "description": "Password disimpan plaintext, gunakan bcrypt",
      "suggestion": "from bcrypt import hashpw, gensalt..."
    }
  ],
  "summary": "Implementasi sudah benar tapi ada 1 issue keamanan kritikal."
}
```

**Model:** Claude Opus 4.7 (review butuh reasoning kuat)
**Trigger ke Coder:** Jika `verdict = changes_requested`, Orchestrator lempar balik ke Coder dengan review notes sebagai konteks.

---

### 4.7 DevOps Agent

**Tanggung jawab:** Packaging, build, dan deployment final.

**Tahapan:**
1. **Dependency lock** — generate `requirements.txt` / `pyproject.toml` final
2. **Build config** — generate `pyinstaller.spec` atau `flet build` config
3. **Build executable** — jalankan PyInstaller / Nuitka via sandbox
4. **Smoke test executable** — coba launch hasil build
5. **Package** — zip + checksum + README
6. **(Opsional)** Push ke GitHub Release / Google Drive

**Input:**
- Project lengkap (yang sudah pass Tester + Reviewer di semua task)
- Target platform (Windows/Linux/macOS)

**Output:**
- `dist/<project_name>-v1.0.0-<platform>.zip`
- `BUILD_REPORT.md`

**Catatan Flet:**
- Flet punya `flet build windows/linux/macos` command bawaan
- Tapi untuk distribusi `.exe` mandiri, PyInstaller lebih fleksibel
- DevOps Agent harus deteksi mana yang lebih cocok per case

**Model:** Claude Sonnet 4.6

---

## 5. Orchestrator — State Machine

### 5.1 State Diagram

```
   [IDLE]
      │ user prompt
      ▼
   [PLANNING] ──fail──► [HUMAN_REVIEW]
      │ ok
      ▼
   [PLAN_APPROVAL] (optional human checkpoint)
      │ approved
      ▼
   [TASK_LOOP] ◄─────────────────┐
      │                          │
      ├─► [INDEXING]             │
      ├─► [DESIGNING] (if UI task)│
      ├─► [CODING]               │
      ├─► [TESTING] ──fail──► [CODING] (retry)
      ├─► [REVIEWING] ──changes_requested──► [CODING] (retry)
      │                          │
      │ all tasks done           │
      ▼                          │
   [INTEGRATION_TEST]            │
      │ ok                       │
      ▼                          │
   [DEPLOYING]                   │
      │ ok                       │
      ▼                          │
   [DONE]                        │
                                 │
   [FAILED] ◄───max retry────────┘
```

### 5.2 State Transition Rules

| Current State | Event | Next State | Side Effect |
|---|---|---|---|
| IDLE | `prompt_received` | PLANNING | Init workspace, save prompt |
| PLANNING | `plan_valid` | PLAN_APPROVAL | Save `plan.json` |
| PLANNING | `plan_invalid` | PLANNING (retry) | Increment retry counter |
| PLAN_APPROVAL | `auto_approve` OR `user_ok` | TASK_LOOP | Set current_task = first |
| TASK_LOOP | `next_task` | INDEXING | Load task context |
| INDEXING | `done` | DESIGNING or CODING | - |
| DESIGNING | `design_ready` | CODING | Save `design.json` |
| CODING | `code_written` | TESTING | Update Indexer |
| TESTING | `tests_pass` | REVIEWING | - |
| TESTING | `tests_fail` AND `retry < 3` | CODING | Pass error log |
| TESTING | `tests_fail` AND `retry >= 3` | FAILED | Notify user |
| REVIEWING | `approved` | TASK_LOOP (next task) | Mark task done |
| REVIEWING | `changes_requested` | CODING | Pass review notes |
| TASK_LOOP | `all_done` | INTEGRATION_TEST | - |
| INTEGRATION_TEST | `pass` | DEPLOYING | - |
| DEPLOYING | `built` | DONE | Save artifact |

### 5.3 Implementasi (Pseudocode)

```python
class Orchestrator:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.state = State.IDLE
        self.state_file = workspace / "state.json"

    def run(self, prompt: str):
        self.transition(State.PLANNING, payload={"prompt": prompt})
        while self.state not in (State.DONE, State.FAILED):
            self.step()
            self.persist_state()
        return self.state == State.DONE

    def step(self):
        agent = self.select_agent_for_state()
        result = agent.execute(self.get_context())
        next_state = self.evaluate_transition(result)
        self.transition(next_state, payload=result)
```

**Key implementation note:** State HARUS persisted ke disk setelah setiap transition. Ini supaya kalau sistem crash, bisa resume.

---

## 6. Sandbox Execution — Strategi Hybrid Bertingkat

Untuk eksekusi kode hasil generate (oleh Tester & DevOps), saya rekomendasikan **3 layer sandbox** yang user bisa pilih:

### 6.1 Layer 1 — Subprocess + Resource Limits (Default, Development)

**Use case:** Development, iterasi cepat, low-risk code
**Mekanisme:**
- Eksekusi via `subprocess.Popen` dengan:
  - `cwd` dipaksa ke workspace project (tidak bisa keluar)
  - Timeout per command (default 60s)
  - Memory limit via `resource.setrlimit` (Linux/macOS) atau Job Object (Windows)
  - Env vars whitelist (hanya yang diperlukan)
- File system: tidak ada chroot, tapi monitoring via watchdog (alert kalau ada write di luar workspace)

**Pros:** Cepat, tidak butuh Docker
**Cons:** Kalau ada `os.system("rm -rf /")` di generated code, bisa berbahaya
**Mitigasi:** Static check sebelum execute (block dangerous calls: `os.system`, `subprocess` calls yang tidak sesuai whitelist, `eval`, `exec`)

### 6.2 Layer 2 — Docker Container (Opt-in, Production-grade)

**Use case:** Generated code dari source tidak terpercaya, atau saat build final
**Mekanisme:**
- Image base: `python:3.11-slim` + dependencies
- Container:
  - Read-only root filesystem
  - Mount workspace sebagai writable volume
  - Network: `--network none` untuk test, atau bridge limited untuk build
  - Resource limits: `--cpus=2 --memory=2g`
  - User: non-root (UID 1000)
- Auto-cleanup setelah selesai

**Pros:** Isolasi kuat, reproducible
**Cons:** Butuh Docker installed, overhead startup

### 6.3 Layer 3 — Remote Sandbox (Future, Skala Tim)

**Use case:** Production, multi-user, agent farm
**Mekanisme:** Service eksternal seperti E2B, Modal, atau self-hosted Firecracker microVMs.
**Pros:** Isolasi maksimal, scalable
**Cons:** Biaya, kompleksitas
**Status:** Out of scope untuk v1, taruh di roadmap

### 6.4 Rekomendasi Default

| Skenario | Sandbox |
|---|---|
| Development di laptop kamu | Layer 1 (subprocess) |
| Build & test final aplikasi | Layer 2 (Docker) |
| Multi-user / production | Layer 3 (remote) |

**Implementasi v1:** Mulai dengan Layer 1 + Layer 2 opt-in. Layer 3 disiapkan interface-nya tapi tidak di-implement.

---

## 7. LLM Router — Hybrid Strategy

### 7.1 Routing Table

| Agent | Task Type | Primary | Fallback | Catatan |
|---|---|---|---|---|
| Planner | Semua | Claude Opus 4.7 | Claude Sonnet 4.6 | Reasoning kritikal |
| Indexer | Embedding | Ollama (`nomic-embed-text`) | OpenAI `text-embedding-3-small` | Volume tinggi → lokal |
| UI/UX | Design spec | Claude Sonnet 4.6 | Claude Opus 4.7 | Balance cost/quality |
| Coder | Scaffold | Ollama (`qwen2.5-coder:14b`) | Claude Sonnet 4.6 | Volume tinggi |
| Coder | Logic kompleks | Claude Sonnet 4.6 | Claude Opus 4.7 | - |
| Coder | Refactor arsitektural | Claude Opus 4.7 | - | Stake tinggi |
| Tester | Generate tests | Claude Sonnet 4.6 | Ollama | - |
| Reviewer | Semua | Claude Opus 4.7 | Claude Sonnet 4.6 | Kualitas kritikal |
| DevOps | Semua | Claude Sonnet 4.6 | Ollama | Tool use intensif |

### 7.2 Estimasi Biaya (per session, asumsi aplikasi medium)

Asumsi: ~30 tasks, masing-masing 1-2 round Coder+Tester+Review.

| Provider | Estimated Tokens | Estimated Cost (USD) |
|---|---|---|
| Claude Opus (Planner + Reviewer) | ~150K in, ~50K out | ~$5.25 |
| Claude Sonnet (Coder + UI/UX + DevOps) | ~800K in, ~200K out | ~$5.40 |
| Ollama lokal | unlimited | $0 |
| **Total per session** | | **~$10-12** |

Tanpa hybrid (semua Opus): **~$45-50/session**.
Penghematan: **~75%**.

### 7.3 Implementasi Router

```python
class LLMRouter:
    def route(self, agent: str, task_type: str, context_size: int) -> LLMClient:
        # Rule-based routing
        if agent == "planner":
            return self.claude_opus
        if agent == "coder" and task_type == "scaffold":
            return self.ollama if self.ollama.healthy() else self.claude_sonnet
        # ... dst
```

**Failover:** Jika Ollama down atau response invalid, otomatis fallback ke Claude.

---

## 8. Shared Workspace — Struktur File

```
workspace/
├── .agent/                          # Internal state agent system
│   ├── state.json                   # Current orchestrator state
│   ├── plan.json                    # Output Planner
│   ├── designs/                     # Output UI/UX (per screen)
│   │   └── expense_form.json
│   ├── reviews/                     # Output Reviewer (per task)
│   │   └── T1.1.json
│   ├── test_results/                # Output Tester (per task)
│   │   └── T1.1.json
│   ├── logs/                        # Per-agent logs
│   │   ├── planner.log
│   │   ├── coder.log
│   │   └── orchestrator.log
│   ├── .vectordb/                   # ChromaDB persistence
│   └── .agentrules                  # Project conventions (auto-generated)
│
├── project/                         # Aplikasi yang sedang dibangun
│   ├── pyproject.toml
│   ├── src/
│   │   └── expense_tracker/
│   │       ├── __init__.py
│   │       ├── main.py              # Entry point Flet
│   │       ├── screens/
│   │       ├── db/
│   │       └── utils/
│   ├── tests/
│   └── README.md
│
└── dist/                            # Output DevOps
    └── expense_tracker-v1.0.0-windows.zip
```

### 8.1 `state.json` Schema

```json
{
  "session_id": "uuid",
  "started_at": "ISO8601",
  "current_state": "CODING",
  "current_task": "T2.3",
  "user_prompt": "...",
  "retry_count": { "T2.3": 1 },
  "completed_tasks": ["T1.1", "T1.2", "T2.1", "T2.2"],
  "failed_tasks": [],
  "metrics": {
    "total_llm_calls": 47,
    "total_cost_usd": 3.21,
    "elapsed_seconds": 1820
  }
}
```

---

## 9. Tech Stack & Dependencies

### 9.1 Core

```toml
[project]
name = "agent-team-builder"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # LLM clients
    "anthropic>=0.40.0",
    "ollama>=0.3.0",

    # Vector DB & embeddings
    "chromadb>=0.5.0",

    # Orchestration & state
    "pydantic>=2.5.0",
    "transitions>=0.9.0",  # FSM library (atau bikin custom)

    # File watching & indexing
    "watchdog>=4.0.0",
    "tree-sitter>=0.21.0",
    "tree-sitter-python>=0.21.0",

    # Sandbox
    "docker>=7.0.0",  # opsional, untuk Layer 2

    # Testing (untuk Tester Agent)
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.6.0",
    "mypy>=1.10.0",

    # Output app stack (akan di-install di workspace, bukan di host)
    # flet, pyinstaller, dll di-resolve oleh Coder/DevOps

    # CLI & UI
    "typer>=0.12.0",
    "rich>=13.7.0",
    "streamlit>=1.35.0",  # dashboard

    # Logging
    "loguru>=0.7.0",
]
```

### 9.2 Output App Stack (yang di-generate)

```
flet>=0.24.0
pyinstaller>=6.5.0
sqlalchemy>=2.0.0  # jika butuh DB
matplotlib>=3.8.0  # jika butuh chart
# ... ditentukan oleh Planner per kasus
```

---

## 10. Struktur Project Source Code

```
agent-team-builder/
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md                  # Dokumen ini
├── PROGRESS.md                      # Tracking development
├── .agentrules                      # Konvensi untuk Cursor AI
│
├── src/
│   └── agent_builder/
│       ├── __init__.py
│       ├── cli.py                   # Entry point CLI
│       │
│       ├── core/
│       │   ├── orchestrator.py      # State machine
│       │   ├── workspace.py         # Workspace management
│       │   ├── state.py             # State models (Pydantic)
│       │   └── exceptions.py
│       │
│       ├── agents/
│       │   ├── base.py              # Base Agent class
│       │   ├── planner.py
│       │   ├── indexer.py
│       │   ├── designer.py
│       │   ├── coder.py
│       │   ├── tester.py
│       │   ├── reviewer.py
│       │   └── devops.py
│       │
│       ├── llm/
│       │   ├── router.py            # LLM Router
│       │   ├── claude_client.py
│       │   ├── ollama_client.py
│       │   └── prompts/             # Prompt templates per agent
│       │       ├── planner.txt
│       │       ├── coder.txt
│       │       └── ...
│       │
│       ├── sandbox/
│       │   ├── base.py
│       │   ├── subprocess_sandbox.py
│       │   └── docker_sandbox.py
│       │
│       ├── indexing/
│       │   ├── chunker.py           # AST-aware chunking
│       │   ├── embedder.py
│       │   └── chroma_store.py
│       │
│       ├── tools/                   # Tool implementations untuk agents
│       │   ├── file_ops.py
│       │   ├── search.py
│       │   └── shell.py
│       │
│       └── dashboard/
│           ├── app.py               # Streamlit app
│           └── components.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── examples/
    ├── todo_app_prompt.txt
    └── expense_tracker_prompt.txt
```

---

## 11. Roadmap Pengembangan

### Fase 1 — Foundation (Minggu 1-2)

**Goal:** Skeleton sistem siap dijalankan, bisa terima prompt tapi belum produktif.

**Deliverables:**
- [ ] Project structure & `pyproject.toml`
- [ ] `core/orchestrator.py` — state machine basic
- [ ] `core/workspace.py` — workspace I/O
- [ ] `core/state.py` — Pydantic models
- [ ] `llm/router.py` — Claude + Ollama clients
- [ ] `llm/claude_client.py`, `llm/ollama_client.py`
- [ ] `agents/base.py` — base Agent class dengan retry logic
- [ ] `sandbox/subprocess_sandbox.py` — Layer 1
- [ ] CLI entry point (`typer`)
- [ ] Logging infrastructure (`loguru`)
- [ ] Unit tests untuk core components

**Success criteria:** CLI bisa dijalankan, baca prompt, init workspace, save state.

---

### Fase 2 — Single Agent E2E (Minggu 3)

**Goal:** Planner + Coder bisa menghasilkan script Python sederhana.

**Deliverables:**
- [ ] `agents/planner.py` lengkap
- [ ] `agents/coder.py` versi basic (tanpa Indexer dulu)
- [ ] Prompt templates Planner & Coder
- [ ] State transitions PLANNING → CODING → DONE
- [ ] Integration test E2E

**Success criteria:** Prompt *"Buatkan CLI calculator yang menerima 2 angka dan operasi"* → menghasilkan file Python yang bisa dijalankan.

---

### Fase 3 — Self-Correction Loop (Minggu 4-5)

**Goal:** Sistem bisa retry otomatis berdasarkan test & review.

**Deliverables:**
- [ ] `agents/tester.py` lengkap
- [ ] `agents/reviewer.py` lengkap
- [ ] Retry logic di Orchestrator (max 3 attempts)
- [ ] State transitions lengkap dengan loop CODING ↔ TESTING ↔ REVIEWING
- [ ] Test result parsing

**Success criteria:** Prompt *"Buatkan aplikasi Flet todo list dengan SQLite"* → aplikasi berjalan, test pass, no review issues critical.

---

### Fase 4 — Full Team & Indexing (Minggu 6-7)

**Goal:** Semua 7 agent aktif, sistem produktif untuk aplikasi medium.

**Deliverables:**
- [ ] `agents/indexer.py` + ChromaDB integration
- [ ] `agents/designer.py` + Flet widget spec library
- [ ] `agents/devops.py` + PyInstaller integration
- [ ] `sandbox/docker_sandbox.py` — Layer 2
- [ ] AST-aware chunker (`tree-sitter`)
- [ ] LLM Router lengkap dengan failover

**Success criteria:** Prompt *"Buatkan aplikasi pencatat pengeluaran dengan grafik bulanan"* → menghasilkan `.exe` yang siap dipakai.

---

### Fase 5 — Dashboard & Polish (Minggu 8)

**Goal:** Observability & UX baik untuk daily use.

**Deliverables:**
- [ ] Streamlit dashboard (live state, logs, metrics, cost)
- [ ] Human-in-the-loop checkpoints (approve plan, etc.)
- [ ] Session replay (resume from crashed state)
- [ ] Configuration profiles (`agent.config.yaml`)
- [ ] Documentation lengkap (user guide + developer guide)
- [ ] Example projects (3-5 sample prompts dengan output)

**Success criteria:** Bisa di-publish sebagai tool internal/open-source.

---

## 12. Risiko & Mitigasi

| Risiko | Probability | Impact | Mitigasi |
|---|---|---|---|
| Infinite retry loop | Medium | High | Hard retry budget per task (max 3) + circuit breaker per session |
| LLM cost explosion | Medium | High | Token budget per session + early stop jika budget habis |
| Generated code merusak file host | Low | Critical | Sandbox layer 1 + static check blocking dangerous calls |
| ChromaDB lambat di codebase besar | Medium | Medium | Lazy indexing + cache + pruning chunk lama |
| Flet API berubah (breaking changes) | Low | Medium | Pin version di `pyproject.toml` template + smoke test |
| Ollama out-of-memory di laptop user | Medium | Medium | Auto-detect VRAM + fallback ke model kecil atau cloud |
| Plan terlalu ambisius (proyek besar) | High | Medium | Planner kasih warning kalau estimasi >50 task, minta narrowing scope |
| State corruption saat crash | Low | High | Atomic write `state.json` (write to tmp + rename) |

---

## 13. Keputusan Terbuka (Open Decisions)

Hal-hal yang perlu kamu putuskan sebelum implementasi:

1. **Apakah perlu multi-user support (v1)?** → Saran: tidak, single-user dulu.
2. **Apakah perlu mendukung non-Flet GUI (mis. PyQt) di v1?** → Saran: tidak, fokus Flet dulu.
3. **Storage untuk session history?** → Saran: SQLite lokal (sesuai pattern Flutter app kamu).
4. **Lisensi project?** → Saran: MIT atau Apache 2.0 jika mau open source.
5. **Repository host?** → GitHub private dulu, public setelah Fase 5.

---

## 14. Appendix

### 14.1 Glossary

- **Agent**: Modul Python yang punya 1 tanggung jawab spesifik dalam pipeline
- **Orchestrator**: State machine yang mengatur urutan eksekusi agent
- **Workspace**: Direktori yang berisi project yang sedang dibangun + state agent
- **Task**: Unit kerja terkecil dalam plan, biasanya = 1 file change
- **Blackboard pattern**: Komunikasi antar agent via shared state, bukan direct call
- **Sandbox**: Environment terisolasi untuk eksekusi kode hasil generate

### 14.2 Referensi Konsep

- **Multi-agent systems**: Pola supervisor + workers (dari literatur AI agent 2024-2025)
- **Blackboard architecture**: Pola klasik AI (Hayes-Roth, 1985), populer kembali di era LLM
- **State machine for agents**: Pendekatan deterministik vs LangGraph yang lebih implicit
- **AST-aware code chunking**: Best practice untuk RAG di codebase (Sweep AI, Cursor)

### 14.3 Anti-Pattern yang Dihindari

- ❌ Agent saling memanggil langsung (tight coupling)
- ❌ Satu agent multi-tasking (susah debug, susah optimize)
- ❌ Tidak ada retry budget (infinite loop risk)
- ❌ Full file rewrite tiap edit (boros token, lost context)
- ❌ Eksekusi kode generate tanpa sandbox (security risk)
- ❌ Single LLM untuk semua task (cost inefficient)
- ❌ State hanya di memory (lost on crash)

---

---

## 15. Dashboard Real-time — UI Specification

### 15.1 Tech Stack & Rasionalisasi

**Framework: Flet** (versi desktop, bukan web mode).

**Alasan pemilihan:**
- Konsisten dengan output app (skill set sama)
- Bisa share komponen UI antara dashboard dan generated app (DRY)
- Cross-platform (Windows/Linux/macOS) tanpa effort tambahan
- Tidak butuh HTTP server / browser → lebih ringan, lebih cepat startup
- Hot reload bagus untuk iterasi UI

**Trade-off yang diterima:**
- Ecosystem chart Flet belum sekaya web (mitigasi: pakai `matplotlib` embedded atau `flet-mpl`)
- Beberapa widget custom perlu di-build sendiri (drag-drop, virtualized list)

### 15.2 Mekanisme Komunikasi Real-time

**Rekomendasi: Hybrid Event Bus + File Watcher (bukan WebSocket).**

**Arsitektur:**

```
┌─────────────────────────────────────────────────────────────┐
│  Process: agent-builder (orchestrator + dashboard)          │
│                                                              │
│   ┌──────────────┐         ┌──────────────────────┐         │
│   │ Orchestrator │─publish─►   In-Memory Bus     │         │
│   │   + Agents   │         │  (asyncio.Queue +    │         │
│   └──────┬───────┘         │   pub/sub registry)  │         │
│          │                  └──────────┬───────────┘         │
│          │ persist                     │ subscribe          │
│          ▼                              ▼                   │
│   ┌──────────────┐                ┌──────────────┐         │
│   │  state.json  │                │  Dashboard   │         │
│   │ (atomic     │                │   (Flet)     │         │
│   │  write)     │                └──────────────┘         │
│   └──────┬───────┘                                          │
└──────────┼──────────────────────────────────────────────────┘
           │
           │ (only used if dashboard runs in separate process)
           ▼
   ┌─────────────────┐
   │ File Watcher   │  ← watchdog library
   │ (fallback)     │
   └─────────────────┘
```

**Mode operasi:**

1. **Mode Single-Process (default, recommended)**
   - Dashboard dan Orchestrator di proses Python sama
   - Komunikasi via `asyncio.Queue` pub/sub (in-memory)
   - Latency: <10ms
   - Tidak ada serialisasi/deserialisasi overhead
   - Simpel: tidak ada socket, port, atau auth

2. **Mode Detached (opsional, untuk monitoring jarak jauh)**
   - Dashboard di proses terpisah (bisa di mesin lain via shared filesystem)
   - Komunikasi via file watcher (`watchdog`) yang memantau `state.json` + `logs/`
   - Latency: 50-200ms (cukup untuk UX dashboard)
   - Robust terhadap crash orchestrator (state ter-persist)

**Implementasi Event Bus (single-process):**

```python
# src/agent_builder/core/event_bus.py
from dataclasses import dataclass
from typing import Callable, Literal
from datetime import datetime
import asyncio

EventType = Literal[
    "task_started", "task_progress", "task_completed",
    "task_failed", "task_blocked", "agent_log",
    "llm_call", "state_changed", "cost_updated"
]

@dataclass
class Event:
    type: EventType
    timestamp: datetime
    payload: dict
    session_id: str

class EventBus:
    def __init__(self):
        self._subscribers: dict[EventType, list[Callable]] = {}
        self._history: list[Event] = []  # untuk replay
        self._max_history = 10_000

    async def publish(self, event: Event):
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        for cb in self._subscribers.get(event.type, []):
            asyncio.create_task(cb(event))

    def subscribe(self, event_type: EventType, callback: Callable):
        self._subscribers.setdefault(event_type, []).append(callback)
```

**Persistensi paralel:**
Setiap event critical (task_started, task_completed, task_failed) juga di-tulis ke `events.jsonl` (append-only log) untuk replay & audit.

### 15.3 Layout Dashboard (4 Tab)

```
┌───────────────────────────────────────────────────────────────┐
│  Logo  Session: Pencatat Pengeluaran   ●Running 28m  [Pause] │
├───────────────────────────────────────────────────────────────┤
│  Tab: [Kanban] [Dependency] [Cost] [Replay]                  │
├───────────────────────────────────────────────────────────────┤
│  Metrics: Progress 12/24 │ LLM 47 │ $3.21 │ Retry 3          │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│              Konten tab aktif di sini                         │
│                                                                │
├───────────────────────────────────────────────────────────────┤
│  Live Activity Feed (selalu visible, max-height 140px)        │
└───────────────────────────────────────────────────────────────┘
```

### 15.4 Tab 1 — Kanban Board (Default View)

**4 kolom:**
1. **Menunggu** (status: `pending`, `blocked_by_dependency`)
2. **Sedang dikerjakan** (status: `running`)
3. **Diblokir** (status: `blocked_retry_exceeded`, `blocked_needs_input`)
4. **Selesai** (status: `done`, `skipped`)

**Komponen task card:**
```python
# src/agent_builder/dashboard/components/task_card.py
import flet as ft

def task_card(task: TaskState, on_click) -> ft.Container:
    agent_color = AGENT_COLORS[task.assigned_agent]
    border_left = None
    if task.status == "running":
        border_left = ft.border.only(left=ft.BorderSide(3, ft.Colors.BLUE_700))
    elif task.status.startswith("blocked"):
        border_left = ft.border.only(left=ft.BorderSide(3, ft.Colors.RED_700))

    return ft.Container(
        on_click=on_click,
        border=border_left or ft.border.all(0.5, ft.Colors.with_opacity(0.15, "#000")),
        border_radius=8,
        padding=10,
        margin=ft.margin.only(bottom=8),
        bgcolor=ft.Colors.WHITE,
        content=ft.Column([
            ft.Text(task.id, size=10, font_family="JetBrains Mono",
                    color=ft.Colors.with_opacity(0.5, "#000")),
            ft.Text(task.title, size=13),
            ft.Row([
                AgentTag(task.assigned_agent),
                TaskStatusIndicator(task)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=4)
    )
```

**Behavior:**
- Click card → buka detail panel (drawer slide-in dari kanan)
- Detail panel berisi: full description, acceptance criteria, file affected, log live, retry history
- Dari detail panel: chat dengan agent (lihat §19), force-retry, skip task, edit & resume

### 15.5 Color Mapping & Status

**Agent colors:**
```python
AGENT_COLORS = {
    "planner":   {"bg": "#EEEDFE", "fg": "#3C3489"},  # purple
    "indexer":   {"bg": "#F1EFE8", "fg": "#444441"},  # gray
    "designer":  {"bg": "#FBEAF0", "fg": "#72243E"},  # pink
    "coder":     {"bg": "#E6F1FB", "fg": "#0C447C"},  # blue
    "tester":    {"bg": "#FAEEDA", "fg": "#633806"},  # amber
    "reviewer":  {"bg": "#E1F5EE", "fg": "#085041"},  # teal/green
    "devops":    {"bg": "#FAECE7", "fg": "#712B13"},  # coral
}
```

**Status states:**
| Status | Indikator visual | Action available |
|---|---|---|
| `pending` | Default card | View details |
| `blocked_by_dependency` | Tag "menunggu T2.1" | View deps |
| `running` | Left border biru + spinner + sub-status | View live log |
| `blocked_retry_exceeded` | Left border merah + reason | Resolve, skip, edit |
| `blocked_needs_input` | Left border merah + question | Respond inline |
| `done` | Check mark + duration | View output |
| `skipped` | Strikethrough | Re-enable |
| `failed_unrecoverable` | Red text + reason | Abort session |

---

## 16. Tab 2 — Dependency Graph (DAG Visualization)

### 16.1 Tujuan

Visualisasi semua task sebagai directed acyclic graph (DAG) supaya user paham:
- Task mana yang critical path (jalur kritis)
- Bottleneck di mana
- Task mana yang bisa paralel
- Dampak kalau satu task gagal

### 16.2 Komponen

**Library:** `flet` tidak punya graph viz built-in, jadi pakai salah satu:
- **Opsi A**: Embed `pyvis` / `networkx` + matplotlib sebagai image
- **Opsi B (recommended)**: Custom Flet canvas pakai `flet.Canvas` + algoritma layout sederhana (Sugiyama atau force-directed)
- **Opsi C**: Embed graphviz output sebagai SVG

**Pilihan:** Opsi B untuk interaktif (klik node, hover tooltip). Fallback ke Opsi A jika graph >50 node.

### 16.3 Layout Algorithm

**Sugiyama (layered) layout** — task disusun layer per layer berdasarkan dependency depth:
- Layer 0: task tanpa dependency (akar)
- Layer N: task yang depend pada task di layer N-1

**Visual encoding:**
- Node color = agent color
- Node border thickness = retry count (tebal = banyak retry)
- Node size = estimated complexity (kecil/medium/besar)
- Edge solid = dependency aktif
- Edge dashed = soft dependency (optional)
- Critical path = highlighted dengan stroke lebih tebal

### 16.4 Interaksi

- Click node → buka task detail (sama seperti Kanban)
- Hover node → tooltip dengan info ringkas
- Filter dropdown → tampilkan hanya status tertentu (e.g., "only blocked")
- Toggle "show completed" → hide/show task selesai untuk fokus ke yang aktif
- Zoom + pan (mouse wheel + drag)

### 16.5 Data Model

```python
# src/agent_builder/core/state.py
class TaskNode(BaseModel):
    id: str
    title: str
    assigned_agent: str
    status: TaskStatus
    depends_on: list[str]
    estimated_complexity: Literal["small", "medium", "large"]
    retry_count: int
    on_critical_path: bool  # computed

def compute_critical_path(tasks: list[TaskNode]) -> set[str]:
    """Longest path dari start ke end node berdasarkan estimated duration."""
    # implementasi: topological sort + dynamic programming
    ...
```

---

## 17. Tab 3 — Cost Breakdown

### 17.1 Tujuan

Real-time visibility soal pengeluaran LLM, supaya:
- User tidak kaget di akhir session
- Bisa identifikasi agent/task mana yang boros
- Bisa set budget cap dan early-stop

### 17.2 Komponen Utama

**A. Top-line metrics:**
- Total cost (USD + IDR converted)
- Budget remaining (jika ada budget cap)
- Burn rate ($/menit)
- ETA biaya total saat selesai (extrapolated)

**B. Breakdown per agent (bar chart horizontal):**
```
Planner    ████████████░░░░░░░░ $1.24 (39%)  [3 calls, Opus]
Reviewer   ████████░░░░░░░░░░░░ $0.87 (27%)  [8 calls, Opus]
Coder      ██████░░░░░░░░░░░░░░ $0.62 (19%)  [22 calls, Sonnet]
Designer   ███░░░░░░░░░░░░░░░░░ $0.31 (10%)  [5 calls, Sonnet]
Tester     ██░░░░░░░░░░░░░░░░░░ $0.17 (5%)   [9 calls, Sonnet]
DevOps     ░░░░░░░░░░░░░░░░░░░░ $0.00 (0%)   [belum mulai]
Indexer    ░░░░░░░░░░░░░░░░░░░░ $0.00 (0%)   [Ollama lokal]
```

**C. Breakdown per model:**
```
Claude Opus 4.7   $2.11  (65%) ────────
Claude Sonnet 4.6 $1.10  (35%) ────
Ollama (local)    $0.00         [free]
```

**D. Trend over time (line chart):**
- X axis: waktu (sejak start session)
- Y axis: cumulative cost
- Forecast line (dashed) → proyeksi sampai selesai

**E. Token usage detail (collapsible table):**
| Agent | Model | Input tokens | Output tokens | Calls | Cost |
|---|---|---|---|---|---|
| Planner | Opus 4.7 | 12,400 | 4,800 | 3 | $1.24 |
| ... | ... | ... | ... | ... | ... |

### 17.3 Budget Alert

User bisa set budget cap saat memulai session:
```python
agent-builder run "Buatkan aplikasi X" --budget 10.00
```

**Alert thresholds:**
- 50% used → notification kuning di dashboard
- 80% used → notification merah + pause planner agent (cegah generate task baru)
- 100% used → auto-pause semua agent, butuh konfirmasi user untuk continue

### 17.4 Implementasi

```python
# src/agent_builder/core/cost_tracker.py
PRICING = {
    "claude-opus-4-7":   {"in": 15.0,  "out": 75.0},   # per 1M tokens
    "claude-sonnet-4-6": {"in": 3.0,   "out": 15.0},
    "ollama":            {"in": 0.0,   "out": 0.0},
}

class CostTracker:
    def __init__(self, event_bus: EventBus, budget_cap: float | None = None):
        self.records: list[CostRecord] = []
        self.budget_cap = budget_cap
        event_bus.subscribe("llm_call", self.on_llm_call)

    async def on_llm_call(self, event: Event):
        p = PRICING[event.payload["model"]]
        cost = (
            event.payload["input_tokens"] * p["in"] +
            event.payload["output_tokens"] * p["out"]
        ) / 1_000_000
        self.records.append(CostRecord(
            agent=event.payload["agent"],
            model=event.payload["model"],
            cost=cost,
            timestamp=event.timestamp
        ))
        await self.check_budget()
```

---

## 18. Tab 4 — Session Replay

### 18.1 Tujuan

Memungkinkan user "memutar ulang" session yang sudah jalan (sedang berjalan atau yang sudah selesai) untuk:
- Debugging: lihat persis langkah mana yang salah
- Learning: pelajari pattern agent
- Demo: tunjukkan ke orang lain
- Audit: bukti reproducibility

### 18.2 Mekanisme

**Source of truth:** `events.jsonl` (append-only event log).

**Setiap line adalah 1 event:**
```jsonl
{"ts":"2026-05-29T14:21:00Z","type":"task_started","task_id":"T2.1","agent":"coder","payload":{...}}
{"ts":"2026-05-29T14:21:03Z","type":"llm_call","agent":"coder","model":"sonnet-4-6","input_tokens":3200,"output_tokens":1100}
{"ts":"2026-05-29T14:22:14Z","type":"task_completed","task_id":"T2.1","duration_s":74}
```

### 18.3 UI Replay Controls

```
┌────────────────────────────────────────────────────────────┐
│  ◄◄  ◄  [▶ Play]  ▶  ►►     Speed: [1x ▼]                 │
│                                                             │
│  ●━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━○              │
│  00:00      14:23 (now)                    28:14 (end)    │
│             ▲ current position                              │
│                                                             │
│  Jump to: [Task started ▼]  [Task failed ▼]  [Blocker ▼]  │
└────────────────────────────────────────────────────────────┘
```

**Controls:**
- Play / Pause
- Step forward / backward (per event)
- Skip ke event tipe tertentu (next task_started, next task_failed, etc.)
- Speed: 0.5x, 1x, 2x, 5x, 10x
- Timeline scrub (drag handle)
- "Jump to interesting moments" — bookmark otomatis untuk: task failed, blocker, milestone completed, cost milestone ($1, $5, $10)

**Kanban board akan rewind:** Saat user scrub timeline, semua status task di Kanban board akan kembali ke state saat itu. Ini "deterministic state reconstruction" — bukan animasi mock, tapi benar-benar replay state.

### 18.4 Branch & Fork

**Fitur advanced (Fase 5+):** dari titik replay tertentu, user bisa "fork" session — clone state dan continue dengan modifikasi (e.g., "ulangi dari T2.6 tapi pakai model Opus instead of Sonnet"). Berguna untuk:
- A/B testing strategi
- Recovery dari kesalahan tanpa rerun dari awal

### 18.5 Implementasi

```python
# src/agent_builder/replay/player.py
class SessionReplayer:
    def __init__(self, events_file: Path):
        self.events = [json.loads(l) for l in events_file.read_text().splitlines()]
        self.position = 0

    def reconstruct_state_at(self, position: int) -> SessionState:
        """Replay events sampai position untuk reconstruct state."""
        state = SessionState.initial()
        for event in self.events[:position]:
            state = state.apply(event)  # pure function: state + event -> new state
        return state
```

**Key principle:** State adalah hasil reduce dari events (event sourcing pattern). Ini bikin replay deterministik dan reliable.

---

## 19. Agent Chat — Direct Conversation

### 19.1 Tujuan

User bisa langsung "ngobrol" dengan agent tertentu untuk:
- Tanya alasan keputusan ("Kenapa kamu pilih SQLite, bukan PostgreSQL?")
- Override keputusan ("Refactor T2.3 pakai pattern Repository")
- Investigasi error ("Kenapa test T2.6 fail terus?")
- Resolve blocker secara interaktif ("Cobalah install pysqlite3-binary")

### 19.2 UI Layout

Chat panel muncul sebagai drawer slide-in dari kanan saat user click task card atau button "Chat with [Agent]".

```
┌───────────────────────────────────────────┐
│  Chat dengan Coder              [X close] │
├───────────────────────────────────────────┤
│  Context: T2.3 — Buat screen tambah       │
│  pengeluaran (Flet)                       │
│                                            │
│  ┌─────────────────────────────────────┐ │
│  │ Coder: Saya sedang menulis main.py │ │
│  │ menggunakan flet.TextField untuk    │ │
│  │ input nominal. Pakai validator      │ │
│  │ untuk angka positif.                │ │
│  └─────────────────────────────────────┘ │
│                                            │
│  ┌─────────────────────────────────────┐ │
│  │ You: Tambahkan juga validasi max    │ │
│  │ 1 miliar rupiah                     │ │
│  └─────────────────────────────────────┘ │
│                                            │
│  ┌─────────────────────────────────────┐ │
│  │ Coder: Oke, saya akan tambahkan     │ │
│  │ validator max_value=1_000_000_000.  │ │
│  │ Apply ke T2.3 sekarang?             │ │
│  │                                      │ │
│  │ [Apply changes] [Cancel]            │ │
│  └─────────────────────────────────────┘ │
├───────────────────────────────────────────┤
│  Type message...              [Send ►]   │
└───────────────────────────────────────────┘
```

### 19.3 Mekanisme

**Setiap chat = ephemeral conversation** dengan context dari task yang sedang dibahas. Bukan stateful per session — agent tidak "ingat" chat sebelumnya, tapi punya akses ke:
- Task details + history
- File yang di-touch agent ini
- Log execution agent ini

**Action buttons** muncul kontekstual:
- "Apply changes" — agent execute saran yang baru saja dibahas
- "Skip task" — mark sebagai skipped
- "Retry with new context" — re-run dengan instruksi tambahan dari chat
- "Switch model" — jalankan ulang dengan model lain (e.g., upgrade ke Opus)

### 19.4 Implementasi Singkat

```python
# src/agent_builder/agents/chat_proxy.py
class AgentChatSession:
    def __init__(self, agent: BaseAgent, task: TaskState, llm_router: LLMRouter):
        self.agent = agent
        self.task = task
        self.history: list[Message] = []
        self.llm = llm_router.route_for_chat(agent.name)

    async def send(self, user_message: str) -> AgentResponse:
        self.history.append({"role": "user", "content": user_message})

        system_prompt = f"""You are the {self.agent.name} agent.
        Current task: {self.task.to_context()}
        Recent log: {self.agent.recent_log()}
        Respond conversationally. If user wants you to do something,
        propose an action and end with [ACTION:apply_changes]
        or [ACTION:retry] tag."""

        response = await self.llm.chat(system_prompt, self.history)
        action = self.parse_action_tag(response.text)
        self.history.append({"role": "assistant", "content": response.text})

        return AgentResponse(text=response.text, suggested_action=action)
```

---

## 20. Update Roadmap (Revised)

Roadmap §11 diperbarui untuk akomodasi dashboard:

### Fase 5 — Dashboard Full Feature (Minggu 8-10, expanded)

**Sebelumnya 1 minggu, sekarang 3 minggu** karena scope lebih besar:

**Minggu 8 — Foundation Dashboard:**
- [ ] Flet app skeleton + routing antar tab
- [ ] Event Bus implementation
- [ ] State reconstruction logic
- [ ] Kanban view (Tab 1) lengkap
- [ ] Live activity feed
- [ ] Task detail drawer

**Minggu 9 — Visualizations:**
- [ ] Dependency graph (Tab 2)
- [ ] Cost breakdown (Tab 3) dengan chart
- [ ] Budget alerts & enforcement
- [ ] Custom Flet canvas component untuk graph

**Minggu 10 — Advanced Features:**
- [ ] Session Replay (Tab 4)
- [ ] Agent Chat drawer (§19)
- [ ] Event log persistence (`events.jsonl`)
- [ ] Replay player dengan controls
- [ ] Polish, dark mode, keyboard shortcuts

**Total proyek menjadi 10 minggu** (sebelumnya 8).

---

## 21. Update Tech Stack

Tambahkan ke §9.1:

```toml
# Dashboard
"flet>=0.24.0",              # GUI framework
"matplotlib>=3.8.0",         # untuk embedded charts
"networkx>=3.2.0",           # untuk DAG layout & critical path
```

**Hapus dari §9.1:** `streamlit` (tidak dipakai lagi karena ganti Flet).

---

## 22. Update Struktur Folder

Tambahkan ke §10:

```
src/agent_builder/dashboard/
├── app.py                       # Entry point Flet app
├── views/
│   ├── kanban.py                # Tab 1
│   ├── dependency_graph.py      # Tab 2
│   ├── cost_breakdown.py        # Tab 3
│   └── replay.py                # Tab 4
├── components/
│   ├── task_card.py
│   ├── agent_tag.py
│   ├── activity_feed.py
│   ├── chat_drawer.py
│   └── graph_canvas.py          # custom DAG renderer
├── state/
│   ├── store.py                 # observable store (subscribe to event bus)
│   └── selectors.py             # computed views (filtered tasks, etc.)
└── theme.py                     # warna agent, dark mode, etc.

src/agent_builder/replay/
├── player.py
└── events_store.py              # baca/tulis events.jsonl
```

---

## 23. Next Step

Setelah dokumen ini di-review dan disetujui:

1. **Setup repository** dengan struktur folder di §10 + §22
2. **Buat `PROGRESS.md`** untuk tracking development (mirip workflow Flutter kamu)
3. **Buat `.agentrules`** & `PROMPTS.md` untuk Cursor AI development
4. **Mulai Fase 1** sesuai roadmap §11 (foundation orchestrator dulu, bukan dashboard)
5. **Dashboard di Fase 5** — setelah core sistem stabil, baru bangun UI

**Catatan:** Dashboard sengaja ditaruh di akhir karena:
- Tanpa core orchestrator yang stabil, dashboard tidak ada data untuk ditampilkan
- Iterasi dashboard akan lebih cepat kalau core sudah generate event yang reliable
- Selama Fase 1-4, gunakan CLI + log file untuk monitoring (cukup untuk dev)

---

**End of Architecture Specification v1.1**

**Changelog:**
- v1.1 (29 Mei 2026): Tambah bab 15-22 (Dashboard, Dependency Graph, Cost Breakdown, Replay, Agent Chat). Update roadmap & tech stack.
- v1.0 (29 Mei 2026): Initial draft.
