# Security notes

## Authentication & tenancy
- JWT bearer tokens (`python-jose`), passwords hashed with bcrypt via passlib.
- **Tenant isolation**: every company-scoped query filters by `company_id` and verifies the requesting user owns the company (404 rather than 403 to avoid resource enumeration). Enforced in `app/api/deps.py` dependencies — routes cannot accidentally skip it.
- Chat sessions, documents, risks, reports all inherit tenancy through their `company_id`.

## File uploads
- Extension + MIME sniffing allow-list: PDF, DOCX, PPTX, XLSX, CSV, TXT only.
- Size cap `MAX_UPLOAD_MB` (default 50) enforced before reading the body into storage.
- Filenames are sanitized (path separators, control chars stripped); stored names are server-generated UUIDs — the original name is metadata only.
- Files live in `UPLOAD_DIR` **outside any web-served path**; downloads stream through an authenticated endpoint that re-checks ownership.
- SHA-256 dedupe per company prevents redundant storage and re-processing.

## Prompt-injection defense
The RAG system prompt contains an explicit defense line: document contents are untrusted *data*, and any instructions embedded in them must be ignored and reported as suspicious. Evidence ids are the only permitted citation mechanism, so a malicious document cannot redirect answers to fabricated sources — the backend maps ids to real pages.

## LLM boundaries
- The model never computes financial figures (deterministic Python), never invents page numbers (backend citation mapping), and never sees other companies' data (scoped retrieval).

## Data handling
- SQLAlchemy ORM with bound parameters everywhere — no string-concatenated SQL.
- CORS is configurable (`CORS_ORIGINS`); the API never logs secrets, tokens or API keys; structured logs carry request ids, not payloads.
- SQLite dev mode exists for convenience; PostgreSQL + pgvector is the supported production path (Docker Compose ships it).
