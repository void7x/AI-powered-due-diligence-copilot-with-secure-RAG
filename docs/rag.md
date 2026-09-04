# RAG & evidence pipeline

The copilot is **not** chat-with-PDF. It answers strictly from a company-scoped evidence base, and every claim carries a citation that the *backend* — not the LLM — resolves to a document and page.

## Indexing

1. **Extraction** — page-aware: PDFs keep page boundaries (`document_pages`), other formats get synthesized pages. Tables are normalized to `{value, currency, unit, period, source_page}` before prose chunking.
2. **Chunking** — section-aware: headings/section markers split text; chunks pack to `CHUNK_SIZE_TOKENS` with `CHUNK_OVERLAP_TOKENS` overlap. Each chunk stores `company_id, document_id, page_start/end, section, fiscal_year, doc_type`.
3. **Embedding** — `OPENAI_EMBEDDING_MODEL` when a key is configured, otherwise a deterministic offline hashing embedder (same interface, tests run offline). Vectors live in pgvector with an ivfflat index; `EMBEDDING_DIM` is configurable.

## Retrieval

`RetrievalService.search()` is hybrid:

- **Vector**: cosine similarity over pgvector.
- **Keyword**: PostgreSQL full-text / ILIKE scoring over chunk text.
- **Score fusion**: weighted sum with per-source **priority boost** (annual_report/10-K rank above investor decks).
- **Metadata filters**: company (always), optional `doc_type`, `fiscal_year`, `section`.
- **Reranker abstraction**: `RERANKER=none|openai` — the interface is stable, so a cross-encoder can be dropped in.

## Answer protocol

The prompt gives the model numbered evidence blocks and forbids outside knowledge; a **prompt-injection defense line** instructs the model to treat document content as data and ignore instructions inside documents.

The model must answer with strict JSON:

```json
{
  "answer": "…",
  "confidence": "high|medium|low",
  "claims": [
    {"text": "…", "type": "fact|analysis|recommendation|uncertainty|contradiction", "sources": [1, 2]}
  ],
  "insufficient_evidence": false
}
```

- Evidence ids (`SOURCE_N`) are the **only** permitted grounding. The backend maps each id back to `document_id + page` and returns typed `citations`; the frontend renders `[Name • p.N]` badges that deep-link into the document viewer at that page.
- If retrieval returns nothing relevant, the pipeline **short-circuits** and returns the insufficient-evidence message without calling the LLM.
- Chat history is stored (`chat_sessions`, `chat_messages`) and session-scoped follow-ups work.

## Offline mode

With no API key, an extractive fallback composes answers from the top evidence passages, keeps the same JSON contract and the same citation mapping — so demos, tests and the eval harness run with zero external calls.

## Evaluation

`backend/tests/test_rag_evaluation.py` + `RAG_BENCHMARK` (in `app/sample_data/generator.py`) define questions with expected document, page and evidence snippet over the synthetic Aurora corpus. The harness measures retrieval correctness (expected page in top-k), citation correctness and answer relevance; run with `pytest tests/test_rag_evaluation.py`.
