"""RAG pipeline: query -> retrieval -> evidence selection -> LLM -> structured,
citation-backed answer. Evidence ids (SOURCE_N) are assigned by this pipeline and
mapped back to real documents/pages - the model can never invent page numbers."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.prompts import templates
from app.services.llm.client import LLMUnavailable, LLMService
from app.services.retrieval.service import Evidence, RetrievalService
from app.utils.text import truncate

VALID_CLAIM_TYPES = {"fact", "analysis", "recommendation", "uncertainty", "contradiction"}
VALID_CONFIDENCE = {"high", "medium", "low"}


@dataclass
class RagResult:
    answer: str
    confidence: str = "medium"
    claims: list[dict] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    insufficient_evidence: bool = False
    provider: str = "offline"

    def as_dict(self) -> dict:
        return {
            "answer": self.answer, "confidence": self.confidence, "claims": self.claims,
            "citations": self.citations, "insufficient_evidence": self.insufficient_evidence,
            "provider": self.provider,
        }


class RAGPipeline:
    def __init__(self, db: Session, settings: Settings, llm: LLMService | None = None) -> None:
        from app.services.embeddings.service import get_embedding_service
        from app.services.retrieval.service import RetrievalService, build_reranker

        self.settings = settings
        self.llm = llm
        self.retrieval = RetrievalService(
            db, get_embedding_service(settings), settings,
            reranker=build_reranker(settings, llm),
        )

    # ------------------------------------------------------------------ main
    def answer(self, company_id: str, question: str, *,
               document_types: list[str] | None = None,
               fiscal_years: list[int] | None = None,
               document_ids: list[str] | None = None) -> RagResult:
        evidence = self.retrieval.retrieve(
            company_id, question, document_types=document_types,
            fiscal_years=fiscal_years, document_ids=document_ids,
        )
        for i, ev in enumerate(evidence, start=1):
            ev.source_id = f"SOURCE_{i}"

        if not evidence:
            return RagResult(
                answer=("I don't have enough evidence in the available documents to answer "
                        "this reliably. Upload or process relevant documents first."),
                confidence="low", claims=[], citations=[], insufficient_evidence=True,
                provider=self.llm.provider if self.llm else "offline",
            )

        citations = [self._citation_payload(ev) for ev in evidence]

        if self.llm and self.llm.available:
            result = self._llm_answer(question, evidence)
        else:
            result = self._offline_answer(question, evidence)
        result.citations = citations
        result.provider = self.llm.provider if self.llm else "offline"
        return result

    # ------------------------------------------------------------------ llm
    def _llm_answer(self, question: str, evidence: list[Evidence]) -> RagResult:
        assert self.llm is not None
        blocks = []
        for ev in evidence:
            blocks.append(
                f"[{ev.source_id}] Document: {ev.document_name} | Type: {ev.document_type} | "
                f"Fiscal year: {ev.fiscal_year} | Page: {ev.page_number} | Section: {ev.section or 'n/a'}\n"
                f"{truncate(ev.text, 1600)}"
            )
        try:
            raw = self.llm.complete_json(
                templates.COPILOT_SYSTEM,
                templates.copilot_user_prompt(question, blocks),
            )
        except LLMUnavailable:
            return self._offline_answer(question, evidence)
        return self._sanitize_llm_output(raw, evidence)

    def _sanitize_llm_output(self, raw: dict, evidence: list[Evidence]) -> RagResult:
        valid_ids = {ev.source_id for ev in evidence}
        by_id = {ev.source_id: ev for ev in evidence}

        answer = str(raw.get("answer") or "").strip() or "No answer was produced."
        confidence = raw.get("confidence") if raw.get("confidence") in VALID_CONFIDENCE else "medium"
        insufficient = bool(raw.get("insufficient_evidence"))

        claims: list[dict] = []
        for claim in raw.get("claims", [])[:12]:
            if not isinstance(claim, dict):
                continue
            text = str(claim.get("text") or "").strip()
            if not text:
                continue
            sources = [s for s in claim.get("sources", []) if isinstance(s, str) and s in valid_ids]
            ctype = claim.get("type") if claim.get("type") in VALID_CLAIM_TYPES else "analysis"
            if not sources:
                # un-sourced company-specific claims are demoted to uncertainty
                ctype = "uncertainty" if ctype == "fact" else ctype
                if not sources:
                    sources = []
            claims.append({"text": truncate(text, 500), "type": ctype, "sources": sources})

        # strip hallucinated [SOURCE_x] refs from the answer text that don't exist
        def _strip_unknown(match: re.Match) -> str:
            return match.group(0) if match.group(1) in valid_ids else ""

        answer = re.sub(r"\[(SOURCE_\d+)\]", _strip_unknown, answer)
        return RagResult(answer=answer, confidence=confidence, claims=claims,
                         insufficient_evidence=insufficient)

    # -------------------------------------------------------------- offline
    def _offline_answer(self, question: str, evidence: list[Evidence]) -> RagResult:
        """Deterministic extractive fallback (offline/demo mode). No generation -
        returns the most relevant evidence as typed FACT claims with citations."""
        top = evidence[:3]
        lines = [f"Offline analysis mode (no AI provider configured). Most relevant evidence for: "
                 f"\"{truncate(question, 120)}\""]
        claims = []
        for ev in top:
            snippet = truncate(" ".join(ev.text.split()), 420)
            lines.append(f"- [{ev.source_id}] {ev.citation_label()}: {snippet}")
            claims.append({"text": snippet, "type": "fact", "sources": [ev.source_id]})
        lines.append("Configure OPENAI_API_KEY for full analyst-grade synthesis.")
        return RagResult(answer="\n".join(lines), confidence="low", claims=claims)

    # ------------------------------------------------------------- citations
    def _citation_payload(self, ev: Evidence) -> dict:
        return {
            "source_id": ev.source_id,
            "document_id": ev.document_id,
            "document_name": ev.document_name,
            "page_number": ev.page_number,
            "section": ev.section,
            "quote": truncate(" ".join(ev.text.split()), 280),
            "relevance": ev.relevance,
        }
