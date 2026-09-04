"""Financial intelligence service: loads stored FinancialMetrics, dedupes across
documents, computes ratios/trends and the deterministic health/growth scores."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, FinancialMetric
from app.services.finance.metrics import (
    PeriodFacts, build_facts, compute_cagrs, compute_period_ratios, revenue_growth,
)

# preferred doc-type order for deduping the same metric reported in several docs
_DOC_TYPE_PRIORITY = {
    "annual_report": 6, "10_k": 6, "financial_statement": 5, "10_q": 4,
    "earnings_report": 3, "investor_presentation": 2, "press_release": 2,
    "market_report": 1, "other": 0,
}

REVENUE = "total_revenue"


@dataclass
class FinancialSnapshot:
    periods: list[PeriodFacts]
    ratios_by_period: dict[str, dict]
    growth: dict
    cagrs: dict
    metric_sources: dict[str, dict]   # (period, metric) -> provenance dict

    @property
    def latest(self) -> PeriodFacts | None:
        return self.periods[-1] if self.periods else None

    def ratio(self, period_label: str, name: str) -> float | None:
        return self.ratios_by_period.get(period_label, {}).get(name)

    def value(self, metric: str, period_label: str | None = None) -> float | None:
        period = period_label or (self.latest.period_label if self.latest else None)
        if not period:
            return None
        for p in self.periods:
            if p.period_label == period:
                return p.values.get(metric)
        return None

    def trend_series(self, metrics: list[str]) -> list[dict]:
        out = []
        for p in self.periods:
            out.append({"period": p.period_label,
                        **{m: p.values.get(m) for m in metrics}})
        return out


def load_snapshot(db: Session, company_id: str) -> FinancialSnapshot:
    rows = db.execute(
        select(FinancialMetric).where(FinancialMetric.company_id == company_id)
    ).scalars().all()
    doc_types: dict[str, str] = {}
    if rows:
        doc_ids = {r.source_document_id for r in rows if r.source_document_id}
        for doc in db.execute(select(Document).where(Document.id.in_(doc_ids))).scalars() if doc_ids else []:
            doc_types[doc.id] = doc.document_type

    best: dict[tuple[str, str], FinancialMetric] = {}
    for row in rows:
        key = (row.period_label, row.metric)
        current = best.get(key)
        rank = (_DOC_TYPE_PRIORITY.get(doc_types.get(row.source_document_id or "", "other"), 0), row.confidence)
        if current is None:
            best[key] = row
        else:
            cur_rank = (_DOC_TYPE_PRIORITY.get(doc_types.get(current.source_document_id or "", "other"), 0),
                        current.confidence)
            if rank > cur_rank:
                best[key] = row

    values_by_period: dict[str, dict[str, float]] = {}
    years_by_period: dict[str, int] = {}
    sources: dict[str, dict] = {}
    import re
    for (label, metric), row in best.items():
        values_by_period.setdefault(label, {})[metric] = row.value
        m = re.search(r"(20\d{2})", label)
        years_by_period[label] = int(m.group(1)) if m else 0
        sources[f"{label}:{metric}"] = {
            "document_id": row.source_document_id, "page": row.source_page,
            "confidence": row.confidence, "currency": row.currency, "unit": row.unit,
        }

    # Plausibility filter: a real reporting period has the revenue line or at
    # least 3 distinct metrics (drops "FY2030" style narrative mentions).
    plausible = {
        label: values for label, values in values_by_period.items()
        if "total_revenue" in values or len(values) >= 3
    }
    values_by_period = plausible
    periods = build_facts(values_by_period, years_by_period)
    ratios = {p.period_label: compute_period_ratios(p) for p in periods}
    return FinancialSnapshot(
        periods=periods, ratios_by_period=ratios,
        growth=revenue_growth(periods), cagrs=compute_cagrs(periods),
        metric_sources=sources,
    )


# ----------------------------------------------------------- deterministic scores
def financial_health_score(snapshot: FinancialSnapshot) -> tuple[int, str]:
    """0-100 blend of margin, liquidity, leverage, cash conversion. Explainable."""
    latest = snapshot.latest
    if latest is None:
        return 0, "unknown"
    parts: list[tuple[float, float]] = []  # (score_0_1, weight)
    gm = snapshot.ratio(latest.period_label, "gross_margin")
    if gm is not None:
        parts.append((min(max(gm / 45.0, 0.0), 1.0), 0.2))
    cr = snapshot.ratio(latest.period_label, "current_ratio")
    if cr is not None:
        parts.append((min(cr / 2.0, 1.0), 0.25))
    de = snapshot.ratio(latest.period_label, "debt_to_equity")
    if de is not None:
        parts.append((min(max(1.0 - de / 2.0, 0.0), 1.0), 0.2))
    ocf_ni = snapshot.ratio(latest.period_label, "ocf_to_net_income")
    if ocf_ni is not None:
        parts.append((min(max(ocf_ni / 1.0, 0.0), 1.0), 0.2))
    fcf_m = snapshot.ratio(latest.period_label, "fcf_margin")
    if fcf_m is not None:
        parts.append((min(max(fcf_m / 12.0, 0.0), 1.0), 0.15))
    if not parts:
        return 0, "unknown"
    score = sum(s * w for s, w in parts) / sum(w for _, w in parts) * 100
    level = "strong" if score >= 70 else "adequate" if score >= 45 else "weak"
    return int(round(score)), level


def growth_potential_score(snapshot: FinancialSnapshot) -> tuple[int, str]:
    latest = snapshot.latest
    if latest is None or len(snapshot.periods) < 2:
        return 0, "unknown"
    cagr_rev = snapshot.cagrs.get(REVENUE)
    if cagr_rev is None:
        # fall back to last YoY revenue growth when CAGR unavailable
        growths = [v for v in snapshot.growth.values() if v is not None]
        cagr_rev = growths[-1] if growths else None
    if cagr_rev is None:
        return 0, "unknown"
    score = min(max(cagr_rev / 25.0, 0.0), 1.0) * 70
    rnd = snapshot.ratio(latest.period_label, "rnd_intensity")
    if rnd is not None:
        score += min(rnd / 8.0, 1.0) * 15
    fcf = snapshot.ratio(latest.period_label, "fcf_margin")
    if fcf is not None:
        score += min(max(fcf, 0.0) / 10.0, 1.0) * 15
    score = int(round(min(score, 100)))
    level = "high" if score >= 65 else "moderate" if score >= 40 else "limited"
    return score, level
