# RAG & evidence pipeline

The copilot is **not** chat-with-PDF. It answers from a company-scoped evidence base, and the backend — not the LLM — maps generated evidence ids to document/page provenance.

## Indexing

1. **Extraction** — page-aware for PDFs; other supported formats receive synthesized page metadata. Tables are normalized before prose chunking.
2. **Chunking** — section-aware: headings/section markers split text; chunks pack to `CHUNK_SIZE_TOKENS` with `CHUNK_OVERLAP_TOKENS` overlap. Chunk metadata includes company, document, page, section, fiscal year and document type.
3. **Embedding** — `OPENAI_EMBEDDING_MODEL` when configured, otherwise a deterministic offline hashing embedder. Vectors use the configured `EMBEDDING_DIM`.

## Retrieval

`RetrievalService` combines vector and keyword candidates, rank-based score fusion and source-priority weighting. Company scoping is mandatory; optional filters include document type and fiscal year. `RERANKER=llm` enables the best-effort LLM reranker, while `RERANKER=none` preserves the fused ordering.

## Answer protocol

The prompt gives the model numbered evidence blocks and treats retrieved document content as **untrusted data**. Instructions found inside evidence must not be followed.

The model is required to return structured JSON:

```json
{
  "answer": "…",
  "confidence": "high|medium|low",
  "claims": [
    {"text": "…", "type": "fact|analysis|recommendation|uncertainty|contradiction", "sources": ["SOURCE_1"]}
  ],
  "insufficient_evidence": false
}
```

Evidence ids (`SOURCE_N`) are assigned by the RAG pipeline, not invented by the model. The backend turns them into citation objects containing the real `document_id`, document name, page and excerpt. The frontend renders citation badges and can open the authenticated document viewer at the cited page.

The pipeline short-circuits when retrieval returns no evidence and returns an insufficient-evidence response without calling the LLM.

Chat sessions and messages are persisted and scoped to both the company and authenticated user.

## Offline mode

With no API key, the extractive fallback returns the most relevant evidence passages as typed fact claims. This keeps demos, tests and evaluation deterministic without external AI calls.

## Evaluation

`backend/tests/test_rag_evaluation.py` uses the synthetic Aurora corpus and `RAG_BENCHMARK` to check retrieval/citation behavior against known document pages and evidence snippets. Run it with `python -m pytest tests/test_rag_evaluation.py -q`.
