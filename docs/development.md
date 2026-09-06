# Development guide

## Repo layout
```text
backend/   FastAPI app (app/), Alembic migrations, tests/
frontend/  Next.js 14 App Router app
docs/      architecture, API, RAG, finance, risk, security, development
docker/    Dockerfiles
data/      local SQLite DB + uploads (gitignored)
scripts/   development/smoke-test helpers
```

## Backend (local, no Docker)
```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp ../.env.example .env            # adjust DATABASE_URL / SECRET_KEY as needed
alembic upgrade head
python -m app.seed                 # optional demo user + synthetic company
uvicorn app.main:app --reload --port 8000
```

- SQLite fallback works for isolated development/tests; Docker uses PostgreSQL + pgvector.
- OpenAI is optional: `AI_PROVIDER=offline` or an empty API key keeps chat/analysis on deterministic offline paths where supported.
- For persistent container deployments, configure `STORAGE_BACKEND=r2` and the `R2_*` settings.

## Frontend (local)
```bash
cd frontend
npm install
cp .env.example .env.local         # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                         # http://localhost:3000
npm run typecheck
npm run test
npm run build
```

## Tests
```bash
cd backend
python -m pytest -q

cd ../frontend
npm run test
npm run typecheck
```

The backend suite covers extraction, chunking, financial math, risk rules, API flows, citation contracts, authentication regressions, job ownership and RAG evaluation. Frontend tests cover formatting and citation contracts.

## Environment
Configuration is loaded from `.env` (see `../.env.example`). Important settings include `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, `OPENAI_EMBEDDING_MODEL`, `EMBEDDING_DIM`, `AI_PROVIDER`, `EMBEDDING_PROVIDER`, `STORAGE_BACKEND`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `CHUNK_SIZE_TOKENS`, `CHUNK_OVERLAP_TOKENS`, `RETRIEVAL_TOP_K`, `RERANKER`, `NEXT_PUBLIC_API_URL`, and `CORS_ORIGINS`.

## Conventions
- Backend routers stay thin; domain logic lives under `app/services/`.
- Financial calculations are pure deterministic functions and should remain independently testable.
- Company/document/report/search access must remain tenant-scoped through authentication dependencies.
- Frontend network access goes through `frontend/lib/api.ts`; UI states should cover loading, empty, error and success paths.
- Never commit `.env`, uploads, `node_modules`, `__pycache__` or real customer documents.

## Adding a risk rule
1. Add the rule in `app/services/risk/engine.py` or the appropriate risk service module.
2. Register/include it in the engine flow and add unit coverage in `backend/tests/test_risk_engine.py`.
3. Verify that any user-visible evidence is linked to a document/page when available.

## Adding a metric
1. Extend the finance extraction/storage model and metric handling.
2. Add ratio/trend logic and test coverage.
3. The existing API schemas and frontend charts should consume the typed output without duplicating financial calculations.
