# Development guide

## Repo layout
```
backend/   FastAPI app (app/), Alembic migrations, tests/
frontend/  Next.js 14 App Router app
docs/      these documents
docker/    Dockerfiles
scripts/   dev helpers (seed, smoke test)
data/      dev SQLite DB + uploads (gitignored except sample/)
```

## Backend (local, no Docker)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env            # adjust DATABASE_URL / SECRET_KEY as needed
alembic upgrade head               # create schema
python -m app.seed                 # demo user + synthetic company
uvicorn app.main:app --reload --port 8000
```
- SQLite fallback works out of the box (the app uses pgvector only when Postgres is configured).
- OpenAI not required: `AI_PROVIDER=offline` (or empty key) runs extraction, rules and RAG fully offline.

## Frontend (local)
```bash
cd frontend
npm install
cp .env.example .env.local         # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                        # http://localhost:3000
npm run typecheck && npm run build # verify
```

## Tests
```bash
cd backend && python -m pytest -q          # 46 tests: units + API flow + RAG eval
cd frontend && npm run test                # vitest unit tests (formatting, citation contract)
cd frontend && npx tsc --noEmit            # type gate (build also type-checks)
```

## Environment
All configuration lives in `.env` (see `../.env.example`). Key variables: `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, `OPENAI_EMBEDDING_MODEL`, `EMBEDDING_DIM`, `AI_PROVIDER`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `CHUNK_SIZE_TOKENS`, `CHUNK_OVERLAP_TOKENS`, `RETRIEVAL_TOP_K`, `RERANKER`, `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS`.

## Conventions
- Backend: routers thin, services fat; pure functions for math in `services/finance/ratios.py`; every DB access tenant-scoped.
- Frontend: no fetch outside `lib/api.ts`; loading/empty/error state on every view; small components; typed API responses in `types/index.ts`.
- Commits of generated files: never commit `.env`, uploads, `node_modules`, `__pycache__`.

## Adding a risk rule
1. Add the rule function in `app/services/risk/rules.py` with thresholds as module constants.
2. Register it in the rule registry; add/extend unit tests in `tests/test_risk_engine.py`.
3. If it maps to a scorecard, update weights in `app/services/risk/scorecards.py`.

## Adding a metric
1. Extend the metric enum + label map in `app/services/finance/` (extraction + storage).
2. Add ratio/test coverage; the API and UI pick it up from the schema.
