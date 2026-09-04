# AI Due Diligence Copilot

An evidence-backed **AI due-diligence platform** for analysts: upload company filings and investor materials, get a page-cited financial/risk/opportunity analysis, a retrieval-augmented copilot, and an exportable due-diligence report — every number and every claim traceable to a document and page.

> This is **not** chat-with-PDF. It is a pipeline: documents → document intelligence → evidence layer → financial intelligence → risk & opportunity engines → RAG copilot → DD report.

## Feature map

```mermaid
flowchart TD
    subgraph Ingestion
        A[Upload PDF/DOCX/PPTX/XLSX/CSV/TXT] --> B[Validate + SHA-256 dedupe]
        B --> C[Page-aware extraction<br/>PyMuPDF / python-docx / python-pptx / openpyxl]
        C --> D[Section-aware semantic chunking]
        D --> E[Embeddings → pgvector]
    end
    subgraph Intelligence
        C --> F[Financial metrics ~18<br/>deterministic ratios]
        C --> G[Risk engine ~17 categories]
        C --> H[Opportunity engine ~10]
        C --> I[Cross-document inconsistency detection]
        F & G & H --> J[Scorecards + management questions]
    end
    subgraph Copilot
        E --> K[Hybrid retrieval<br/>vector + keyword + filters + reranker]
        K --> L[SOURCE_N evidence → LLM]
        L --> M[Structured answer + citations]
    end
    G & H & I & F --> N[13-section DD report<br/>HTML / print-to-PDF / JSON]
```

### What makes it trustworthy
- **Backend-mapped citations** — the LLM may only cite `SOURCE_N` ids; the backend resolves them to document + page. The frontend never trusts model-provided page numbers.
- **Deterministic financial math** — all ratios/trends computed by unit-tested pure Python; the LLM never does arithmetic.
- **Typed claims** — answers separate `fact | analysis | recommendation | uncertainty | contradiction`, with an explicit insufficient-evidence state.
- **Explainable risks** — every finding carries signals, thresholds, evidence quotes, "What we found / Why it matters / Potential impact / What to investigate".
- **Safe by default** — tenant isolation, sanitized uploads, size limits, prompt-injection defense line, offline mode with zero external calls.

## Tech stack
- **Frontend**: Next.js 14 (App Router) · React 18 · TypeScript · Tailwind CSS · Recharts · Lucide
- **Backend**: FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic
- **Database**: PostgreSQL + pgvector (SQLite fallback for pure-local dev)
- **Documents**: PyMuPDF, python-docx, python-pptx, openpyxl, pandas/numpy
- **AI**: OpenAI chat + embeddings via env config — with a deterministic offline fallback so everything runs without an API key
- **Tests**: pytest (46 tests incl. RAG eval harness) · TypeScript build-time checks

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
# frontend  → http://localhost:3000
# API docs  → http://localhost:8000/docs
# demo login → demo@example.com / demo1234
```

The checked-in `.env.example` is configured for a **local/demo deployment**: it supplies working Docker database credentials, creates the demo user, and enables the synthetic demo-data seed. Change these values and disable demo seeding for staging/production. The Docker backend runs migrations automatically before starting the API.

The demo seed creates **Aurora Industrial Group** with synthetic filings covering growth, rising debt, margin decline, customer concentration, an expansion opportunity, and a deliberate two-document contradiction.

## Local development (no Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env                 # change DATABASE_URL to the SQLite fallback if desired
alembic upgrade head
python -m app.seed                      # demo user + synthetic company
uvicorn app.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
cp .env.example .env.local              # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                             # http://localhost:3000
```

For a completely isolated local backend without Docker, use the SQLite fallback in `backend/app/core/config.py` or set a SQLite `DATABASE_URL` explicitly.

## Tests

```bash
cd backend && python -m pytest -q       # units (ratios, risk rules, chunking, extraction) + API flow + RAG eval
cd frontend && npx tsc --noEmit
```

The RAG evaluation harness (`tests/test_rag_evaluation.py`, benchmark corpus in `app/sample_data/generator.py`) scores retrieval & citation correctness against known page locations in the synthetic documents.

## Layout

```
backend/app/{api,models,schemas,services/*,prompts,core}
frontend/app/{login,dashboard,companies/[id]/*,reports/[reportId]}
frontend/components   reusable UI (MetricCard, RiskCard, CitationBadge, DocumentViewer, …)
docs/                 architecture, rag, financial-analysis, risk-engine, api, security, development
docker/               backend & frontend Dockerfiles
scripts/              seed + smoke-test helpers
```

## Configuration
See `.env.example` — database, secret key, OpenAI models/dimension, upload limits, chunking tokens, retrieval top-k, reranker, CORS, and demo toggles. Never commit a real `.env` or production secrets.

## Disclaimer
Analytical assistance only — not financial, legal, tax, or investment advice. Every screen and report states this.
