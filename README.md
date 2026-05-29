# Agent Team Builder

Multi-agent AI system that autonomously builds Flet desktop applications from natural language prompts.

- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) v1.1
- **Progress:** [PROGRESS.md](PROGRESS.md)
- **Cursor team workflow:** [AGENTS.md](AGENTS.md), [README_SETUP.md](README_SETUP.md)

## Quick Start

### Prerequisites

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/) (required for full pipeline)
- [Ollama](https://ollama.com/) (optional; local models for scaffold/embeddings)

### Setup

```powershell
cd "g:\baru 2026\april\AI"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# Edit .env — set ANTHROPIC_API_KEY
```

### Verify installation

```powershell
agent-builder --help
agent-builder doctor
agent-builder run "Buatkan todo app dengan Flet"
agent-builder status
agent-builder resume
python -m agent_builder version
pytest
ruff check .
```

### Dashboard (recommended)

```powershell
pip install -e ".[dashboard]"
agent-builder dashboard
```

Open **Tab Kontrol** to start builds, resume sessions, and run environment checks from the UI. See [docs/dashboard.md](docs/dashboard.md).

### Run from CLI

```powershell
agent-builder run "Buatkan aplikasi todo list dengan Flet dan SQLite"
```

Same as **Mulai build** in the dashboard Kontrol tab.

## Development

```powershell
pip install -e ".[dev]"
pre-commit install
pre-commit run --all-files
```

Optional dependency groups:

- `pip install -e ".[docker]"` — Docker sandbox (Layer 2)
- `pip install -e ".[dashboard]"` — Flet dashboard (5 tabs: Kontrol, Kanban, Dependency, Cost, Replay)

## Project layout

```
src/agent_builder/   # Application package
tests/                 # unit / integration / e2e
examples/              # Sample prompts
workspace/             # Runtime output (gitignored)
```

## License

MIT (see project configuration).
