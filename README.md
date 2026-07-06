<div align="center">

# FinAgent

**A local-first AI agent for your bank statements.**

Upload a PDF or CSV, then ask questions in plain language — *"what am I spending the most on"*, *"compare March and February"*, *"find recurring subscriptions"*. Everything runs, and stays, on your own machine.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/typescript-5-3178C6?logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)

</div>

<p align="center">
  <img src="docs/screenshots/chat-light.png" width="49%" alt="FinAgent — light theme" />
  <img src="docs/screenshots/chat-dark.png" width="49%" alt="FinAgent — dark theme" />
</p>

## Features

- **Statement ingestion** — CSV and PDF (native text extraction via PyMuPDF, OCR fallback via Tesseract for scans), automatic bank detection and file renaming.
- **Natural-language chat** over your own data, streamed live over SSE, with a transparent log of every tool call the agent makes.
- **Text-to-SQL** — the agent writes and runs its own read-only SQL against your transactions (table whitelist, forced `LIMIT`, `SELECT`-only, validated with `sqlglot`).
- **Charts in the chat** — metrics, donut/bar/line charts, tables.
- **Auto-categorization** — ~60 built-in merchant rules, LLM fallback with per-merchant caching, and a review screen for anything it isn't confident about.
- **@-mentions** — point a question at a specific file or folder, or let the agent infer scope from the question itself.
- **RAG knowledge base** about bank statement formats and categorization rules (LlamaIndex + Qdrant).
- **MLflow tracing** of every agent run — fully local, no external service.
- Light/dark theme. Zero telemetry.

## Quick Start

Requires Docker and Docker Compose.

```bash
git clone https://github.com/FluDex7/FinAgent.git
cd FinAgent
cp .env.example .env   # set OPENAI_API_KEY, or switch to Ollama — see Configuration below
docker compose up --build
```

- UI: http://localhost:3000
- API: http://localhost:8000 (`/health` for an environment check)

## Architecture

FinAgent draws a hard line between three AI libraries, on purpose:

| Library | Role |
|---|---|
| **LangGraph** | Orchestration only — the model↔tools graph for a single chat turn |
| **LangChain** | LLM wrappers (`ChatOpenAI` / `ChatOllama`) and tool definitions (`@tool`, `StructuredTool`) |
| **LlamaIndex + Qdrant** | Retrieval only, for RAG — never orchestration |

The backend is organized by feature, not by layer: each module under `app/modules/` owns its `router.py` / `service.py` / `repository.py` / `schemas.py` / `models.py`, and never touches another module's tables directly — only through that module's service.

## Tech Stack

**Backend** — FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL · LangChain / LangGraph · LlamaIndex · Qdrant · sqlglot · PyMuPDF + Tesseract OCR · MLflow · [uv](https://docs.astral.sh/uv/)

**Frontend** — React 19 · TypeScript · Vite · Tailwind CSS v4 · Zustand · Recharts

## Configuration

All variables live in [`.env.example`](.env.example).

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://finagent:finagent@localhost:5432/finagent` | Postgres connection |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant connection (RAG) |
| `LLM_PROVIDER` | `openai` | `openai` or `ollama` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `gpt-4o-mini` | Required if `LLM_PROVIDER=openai` |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | `http://localhost:11434` / `mistral` | Required if `LLM_PROVIDER=ollama` — fully offline |
| `STATEMENTS_DIR` | `./data` | Where uploaded statements are stored |
| `MLFLOW_TRACKING_URI` | `sqlite:///./mlflow.db` | Local MLflow tracking store |
| `MLFLOW_EXPERIMENT_NAME` | `finagent` | MLflow experiment name |

Go fully offline with Ollama:

```env
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral
```

Under Docker Compose, `OLLAMA_HOST=http://host.docker.internal:11434` reaches an Ollama instance running on the host — already wired up in `docker-compose.yml`.

## Local Development

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20+, PostgreSQL, and Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-rus`).

```bash
# Postgres + Qdrant are easiest via Docker, even if you run backend/frontend locally
docker compose up -d postgres qdrant

# Backend
cd backend
cp ../.env.example .env   # Settings looks for .env in the current directory
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to localhost:8000
```

### Tests & Linting

```bash
cd backend && uv run pytest && uv run ruff check . && uv run mypy app/
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```

## MLflow Tracing

Every agent turn — model calls, tool calls, graph branches — is traced automatically via `mlflow.langchain.autolog()`, fully locally, no telemetry.

With `docker compose up`, the UI is already served at http://localhost:5000. For local (non-Docker) dev, run it yourself:

```bash
cd backend
uv run mlflow ui --backend-store-uri sqlite:///./mlflow.db
```

Open http://localhost:5000 to see the call tree for each chat turn: `agent → chat model → tools → plot_chart → agent → ...`.

## Backup & Restore

Your actual data lives in two places: the Postgres database (categories, merchant rules, transactions, chat history) and the `data/` folder (raw statement files). Qdrant's RAG index rebuilds itself from static knowledge files on first use — nothing to back up there.

```bash
# On the old machine
docker compose up -d postgres
scripts/backup.sh
# → finagent-backup-YYYYMMDD-HHMMSS.tar.gz

# Copy the archive over, then on the new machine:
docker compose up -d postgres
scripts/restore.sh finagent-backup-YYYYMMDD-HHMMSS.tar.gz
```

## Project Structure

```
FinAgent/
├── docker-compose.yml   postgres + qdrant + backend + frontend
├── scripts/             backup.sh / restore.sh
├── backend/
│   ├── app/
│   │   ├── core/          config, DB (unit-of-work), health checks, MLflow, shared schemas
│   │   ├── shared/        LLM/embedding provider factory
│   │   └── modules/
│   │       ├── statements/      upload, CSV/PDF+OCR parsing, document tree
│   │       ├── transactions/    transactions, categories, merchants
│   │       ├── categorization/  rules + LLM categorization, review endpoints
│   │       ├── agent/           LangGraph graph, SSE streaming, chats
│   │       └── tools/           sql_query, plot_chart, compare_periods, resolve_scope, rag_lookup, read_document
│   ├── migrations/       Alembic
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── api/           typed client + SSE parser
    │   ├── store/         Zustand
    │   └── components/
    │       ├── blocks/    metrics/donut/bars/line/table (recharts, lazy-loaded)
    │       └── modals/    upload / settings
    └── Dockerfile         nginx serving the build, proxying /api
```

## Contributing

Issues and pull requests are welcome. Please run the tests and linters above before submitting.

## License

[MIT](LICENSE) © Romanov Danil
