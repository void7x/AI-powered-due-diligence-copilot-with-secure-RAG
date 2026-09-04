"""Hybrid retrieval: vector similarity + keyword relevance + metadata filtering.

Always scoped to a company (tenant isolation). On PostgreSQL, vector search is
pushed down to pgvector; on SQLite the same scoring runs in Python so tests and
local dev need no database server. RRF fusion + source-priority weighting feed
an optional reranker abstraction.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Document, DocumentChunk
from app.services.embeddings.service import BaseEmbedder

SOURCE_PRIORITY: dict[str, float] = {
    "annual_report": 1.00, "10_k": 1.00, "financial_statement": 0.95,
    "10_q": 0.90, "earnings_report": 0.90, "investor_presentation": 0.85,
    "market_report": 0.80, "press_release": 0.75, "other": 0.70,
}

_RRF_K = 60


@dataclass
class Evidence:
    chunk_id: str
    document_id: str
    document_name: str
    document_type: str
    fiscal_year: int | None
    page_number: int
    section: str
    text: str
    vector_rank: int | None = None
    keyword_rank: int | None = None
    score: float = 0.0
    source_id: str = ""            # assigned as SOURCE_1..N by the RAG layer
    meta: dict = field(default_factory=dict)

    @property
    def relevance(self) -> float:
        return round(min(1.0, self.score), 3)

    def citation_label(self) -> str:
        year = f" {self.fiscal_year}" if self.fiscal_year else ""
        return f"{self.document_name}{year} · p.{self.page_number}"


class Reranker:
    """Reranker abstraction - swap in an LLM or cross-encoder implementation."""

    name = "identity"

    def rerank(self, question: str, evidence: list[Evidence]) -> list[Evidence]:
        return evidence


class LLMReranker(Reranker):
    name = "llm"

    def __init__(self, llm) -> None:
        self._llm = llm

    def rerank(self, question: str, evidence: list[Evidence]) -> list[Evidence]:
        try:  # best-effort; retrieval must survive reranker failures
            import json
            listing = "\n".join(f"[{i}] {e.citation_label()}: {e.text[:200]}" for i, e in enumerate(evidence))
            raw = self._llm.complete_json(
                "Rank evidence by usefulness for the question. Respond as JSON.",
                f'Question: {question}\n\nEvidence:\n{listing}\n\n'
                'Return {\"order\": [indices best-first]}', max_tokens=300)
            order = [int(i) for i in raw.get("order", []) if isinstance(i, int) and 0 <= i < len(evidence)]
            rest = [i for i in range(len(evidence)) if i not in order]
            return [evidence[i] for i in order + rest]
        except Exception:  # noqa: BLE001
            return evidence


def build_reranker(settings: Settings, llm=None) -> Reranker:
    if settings.reranker == "llm" and llm is not None and getattr(llm, "available", False):
        return LLMReranker(llm)
    return Reranker()


class RetrievalService:
    def __init__(self, db: Session, embeddings: BaseEmbedder, settings: Settings,
                 reranker: Reranker | None = None) -> None:
        self.db = db
        self.embeddings = embeddings
        self.settings = settings
        self.reranker = reranker or Reranker()

    # ------------------------------------------------------------- candidates
    def _fetch_rows(self, company_id: str, document_types: list[str] | None,
                    fiscal_years: list[int] | None, document_ids: list[str] | None):
        stmt = (
            select(DocumentChunk, Document.filename)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.company_id == company_id)
        )
        if document_types:
            stmt = stmt.where(DocumentChunk.document_type.in_(document_types))
        if fiscal_years:
            stmt = stmt.where(DocumentChunk.fiscal_year.in_(fiscal_years))
        if document_ids:
            stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))
        return self.db.execute(stmt).all()

    def _vector_candidates(self, question_vec: list[float], rows) -> list[tuple[DocumentChunk, str, float]]:
        qv = np.asarray(question_vec, dtype="float32")
        scored: list[tuple[DocumentChunk, str, float]] = []
        for chunk, filename in rows:
            emb = chunk.embedding
            if emb is None:
                continue
            if isinstance(emb, str):  # pgvector text representation safety
                try:
                    emb = [float(x) for x in emb.strip("[]").split(",")]
                except ValueError:
                    continue
            vec = np.asarray(emb, dtype="float32")
            denom = (np.linalg.norm(qv) * np.linalg.norm(vec)) or 1.0
            sim = float(np.dot(qv, vec) / denom)
            scored.append((chunk, filename, sim))
        scored.sort(key=lambda t: t[2], reverse=True)
        return scored[: self.settings.retrieval_candidate_k]

    def _keyword_candidates(self, terms: list[str], rows) -> list[tuple[DocumentChunk, str, float]]:
        if not terms:
            return []
        scored: list[tuple[DocumentChunk, str, float]] = []
        for chunk, filename in rows:
            text_l = chunk.text.lower()
            hits = sum(1 for t in terms if t in text_l)
            if hits:
                scored.append((chunk, filename, hits / len(terms)))
        scored.sort(key=lambda t: (t[2], len(t[0].text)), reverse=True)
        return scored[: self.settings.retrieval_candidate_k]

    # ---------------------------------------------------------------- public
    def retrieve(self, company_id: str, question: str, *,
                 document_types: list[str] | None = None,
                 fiscal_years: list[int] | None = None,
                 document_ids: list[str] | None = None,
                 top_k: int | None = None,
                 keyword_only: bool = False) -> list[Evidence]:
        from app.utils.text import keywords

        rows = self._fetch_rows(company_id, document_types, fiscal_years, document_ids)
        if not rows:
            return []

        vector_scored: list[tuple[DocumentChunk, str, float]] = []
        if not keyword_only:
            qvec = self.embeddings.embed_query(question)
            vector_scored = self._vector_candidates(qvec, rows)
        terms = keywords(question)[:12]
        keyword_scored = self._keyword_candidates(terms, rows)

        fused: dict[str, dict] = {}
        for rank, (chunk, filename, _sim) in enumerate(vector_scored, start=1):
            fused.setdefault(chunk.id, {"chunk": chunk, "filename": filename,
                                        "v_rank": rank, "k_rank": None})
        for rank, (chunk, filename, kscore) in enumerate(keyword_scored, start=1):
            entry = fused.setdefault(chunk.id, {"chunk": chunk, "filename": filename,
                                                "v_rank": None, "k_rank": rank})
            entry["k_rank"] = rank
            if kscore >= 0.6 and entry["v_rank"] is None:
                entry["v_rank"] = len(vector_scored) + rank  # lexical fallback participates weakly

        for entry in fused.values():
            score = 0.0
            if entry["v_rank"] is not None:
                score += 1.0 / (_RRF_K + entry["v_rank"])
            if entry["k_rank"] is not None:
                score += 0.8 / (_RRF_K + entry["k_rank"])
            priority = SOURCE_PRIORITY.get(entry["chunk"].document_type, 0.7)
            entry["score"] = score * (0.9 + 0.2 * priority)

        ordered = sorted(fused.values(), key=lambda e: e["score"], reverse=True)
        evidence = [
            Evidence(
                chunk_id=e["chunk"].id,
                document_id=e["chunk"].document_id,
                document_name=e["filename"],
                document_type=e["chunk"].document_type,
                fiscal_year=e["chunk"].fiscal_year,
                page_number=e["chunk"].page_number,
                section=e["chunk"].section,
                text=e["chunk"].text,
                vector_rank=e["v_rank"],
                keyword_rank=e["k_rank"],
                score=e["score"],
            )
            for e in ordered
        ]
        evidence = self.reranker.rerank(question, evidence)
        return evidence[: top_k or self.settings.retrieval_top_k]

    def search(self, company_id: str, query: str, *,
               document_types: list[str] | None = None,
               fiscal_years: list[int] | None = None,
               limit: int = 20) -> list[Evidence]:
        return self.retrieve(company_id, query, document_types=document_types,
                             fiscal_years=fiscal_years, top_k=limit, keyword_only=True)
