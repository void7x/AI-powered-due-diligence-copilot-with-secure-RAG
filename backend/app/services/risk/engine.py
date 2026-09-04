"""Explicit, deterministic risk engine.

Rules run over computed financial facts and extracted signals - NOT over LLM
output. The LLM (optional) only enriches the narrative explanation. Every risk
carries: category, severity, score, signals, explanation, impact, evidence,
confidence and recommended follow-up.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import Settings
from app.models.enums import RiskSeverity
from app.services.finance.service import FinancialSnapshot


@dataclass
class DetectedRisk:
    category: str
    title: str
    severity: RiskSeverity
    score: float
    explanation: str
    why_it_matters: str
    potential_impact: str
    recommendation: str
    confidence: str = "high"
    detected_signals: dict = field(default_factory=dict)
    evidence_quote: str = ""
    evidence_hint_metric: str = ""      # (period, metric) to resolve provenance later
    evidence_period: str = ""


SEVERITY_ORDER = {RiskSeverity.LOW: 0, RiskSeverity.MEDIUM: 1, RiskSeverity.HIGH: 2, RiskSeverity.CRITICAL: 3}
_SEVERITY_WEIGHT = {RiskSeverity.LOW: 25.0, RiskSeverity.MEDIUM: 50.0, RiskSeverity.HIGH: 75.0, RiskSeverity.CRITICAL: 95.0}


def severity_from_score(score: float) -> RiskSeverity:
    if score >= 80:
        return RiskSeverity.CRITICAL
    if score >= 60:
        return RiskSeverity.HIGH
    if score >= 35:
        return RiskSeverity.MEDIUM
    return RiskSeverity.LOW


def _scale(value: float, low: float, high: float) -> float:
    """Map value from [low, high] to [0, 100], clamped."""
    if high <= low:
        return 0.0
    return max(0.0, min(100.0, (value - low) / (high - low) * 100))


# --------------------------------------------------------------------- rules
def rule_leverage(snapshot: FinancialSnapshot, settings: Settings) -> DetectedRisk | None:
    debt = [p.values.get("total_debt") for p in snapshot.periods]
    revenue = [p.values.get("total_revenue") for p in snapshot.periods]
    if len(snapshot.periods) < 2 or None in (debt[-2], debt[-1], revenue[-2], revenue[-1]):
        return None
    debt_growth = (debt[-1] - debt[-2]) / abs(debt[-2])          # type: ignore[operator]
    revenue_growth = (revenue[-1] - revenue[-2]) / abs(revenue[-2])  # type: ignore[operator]
    gap = debt_growth - revenue_growth
    if gap < settings.leverage_gap_threshold:
        return None
    last = snapshot.periods[-1]
    d2e = snapshot.ratio(last.period_label, "debt_to_ebitda")
    de = snapshot.ratio(last.period_label, "debt_to_equity")
    score = _scale(gap, 0.02, 0.25) * 0.45
    if d2e is not None:
        score += _scale(d2e, 1.0, 3.5) * 0.35
    if de is not None:
        score += _scale(de, 0.5, 2.0) * 0.2
    severity = severity_from_score(score)
    last_label = last.period_label
    prev = snapshot.periods[-2].period_label
    return DetectedRisk(
        category="leverage", title="Rising leverage outpacing revenue growth",
        severity=severity, score=round(score, 1),
        explanation=(f"Total debt grew {debt_growth * 100:.1f}% from {prev} to {last_label} "
                     f"(vs revenue growth of {revenue_growth * 100:.1f}%)."),
        why_it_matters="Debt increasing materially faster than revenue raises refinancing and interest pressure.",
        potential_impact="Higher interest expense, reduced financial flexibility, potential covenant pressure.",
        recommendation="Investigate the purpose, maturity profile and repayment schedule of the additional borrowing.",
        confidence="high",
        detected_signals={"debt_growth_pct": round(debt_growth * 100, 2),
                          "revenue_growth_pct": round(revenue_growth * 100, 2),
                          "gap_pts": round(gap * 100, 2),
                          "debt_to_ebitda": d2e},
        evidence_hint_metric="total_debt", evidence_period=last_label,
    )


def rule_customer_concentration(snapshot: FinancialSnapshot, settings: Settings) -> DetectedRisk | None:
    latest = snapshot.latest
    if latest is None:
        return None
    conc = latest.values.get("top3_customer_revenue_pct")
    if conc is None or conc < settings.concentration_threshold_pct:
        return None
    score = _scale(conc, settings.concentration_threshold_pct, 50.0)
    severity = severity_from_score(score)
    return DetectedRisk(
        category="customer_concentration",
        title="Material customer concentration",
        severity=severity, score=round(score, 1),
        explanation=f"{conc:.0f}% of revenue comes from the top three customers in {latest.period_label}.",
        why_it_matters="Heavy reliance on a small number of customers concentrates revenue risk.",
        potential_impact="Loss of a major customer could materially affect revenue and margins.",
        recommendation="Ask for customer-level revenue breakdown, contract renewal dates and churn protections.",
        confidence="high",
        detected_signals={"top3_customer_revenue_pct": conc,
                          "threshold_pct": settings.concentration_threshold_pct},
        evidence_hint_metric="top3_customer_revenue_pct", evidence_period=latest.period_label,
    )


def rule_liquidity(snapshot: FinancialSnapshot, settings: Settings) -> DetectedRisk | None:
    latest = snapshot.latest
    if latest is None:
        return None
    cr = snapshot.ratio(latest.period_label, "current_ratio")
    qr = snapshot.ratio(latest.period_label, "quick_ratio")
    if cr is None:
        return None
    if cr >= settings.current_ratio_floor and (qr is None or qr >= settings.quick_ratio_floor):
        return None
    worst = cr if qr is None else min(cr, qr)
    floor = settings.current_ratio_floor if cr <= (qr if qr is not None else cr) else settings.quick_ratio_floor
    score = _scale(floor - worst if floor > worst else 0.0, 0.0, floor)
    severity = severity_from_score(score)
    return DetectedRisk(
        category="liquidity", title="Liquidity below comfortable levels",
        severity=severity, score=round(score, 1),
        explanation=(f"Current ratio is {cr:.2f}" + (f" and quick ratio is {qr:.2f}" if qr is not None else "")
                     + f" in {latest.period_label}."),
        why_it_matters="Thin short-term liquidity can force expensive financing in a downturn.",
        potential_impact="Working-capital strain; potential difficulty meeting near-term obligations.",
        recommendation="Review working-capital cycle, committed credit lines and near-term maturities.",
        confidence="high",
        detected_signals={"current_ratio": cr, "quick_ratio": qr,
                          "current_ratio_floor": settings.current_ratio_floor},
        evidence_hint_metric="current_assets", evidence_period=latest.period_label,
    )


def rule_cash_conversion(snapshot: FinancialSnapshot, _settings: Settings) -> DetectedRisk | None:
    latest = snapshot.latest
    if latest is None or len(snapshot.periods) < 2:
        return None
    ni = latest.values.get("net_income")
    ocf = latest.values.get("operating_cash_flow")
    if ni is None or ocf is None:
        return None
    ratio_ocf_ni = snapshot.ratio(latest.period_label, "ocf_to_net_income")
    negative_ocf_positive_ni = ocf < 0 < ni
    weak_conversion = ratio_ocf_ni is not None and ratio_ocf_ni < 0.5 and len(snapshot.periods) >= 2
    if not (negative_ocf_positive_ni or weak_conversion):
        return None
    score = 85.0 if negative_ocf_positive_ni else _scale(0.5 - (ratio_ocf_ni or 0), 0.0, 0.5) * 60 + 20
    severity = severity_from_score(score)
    if negative_ocf_positive_ni:
        detail = (f"Operating cash flow is negative ({ocf:,.1f}) while net income is positive "
                  f"({ni:,.1f}) in {latest.period_label}.")
    else:
        detail = (f"Operating cash flow is only {ratio_ocf_ni:.0%} of net income "
                  f"in {latest.period_label}.")
    return DetectedRisk(
        category="cash_flow", title="Weak cash conversion of reported earnings",
        severity=severity, score=round(score, 1),
        explanation=detail,
        why_it_matters="Earnings not converting to operating cash can signal aggressive recognition or working-capital stress.",
        potential_impact="Quality-of-earnings concern; potential future restatements or funding needs.",
        recommendation="Perform a quality-of-earnings review: receivables ageing, revenue recognition policy, working-capital swings.",
        confidence="high",
        detected_signals={"net_income": ni, "operating_cash_flow": ocf,
                          "ocf_to_net_income": ratio_ocf_ni},
        evidence_hint_metric="operating_cash_flow", evidence_period=latest.period_label,
    )


def rule_margin_compression(snapshot: FinancialSnapshot, settings: Settings) -> DetectedRisk | None:
    if len(snapshot.periods) < 2:
        return None
    last, prev = snapshot.periods[-1], snapshot.periods[-2]
    om_now = snapshot.ratio(last.period_label, "operating_margin")
    om_prev = snapshot.ratio(prev.period_label, "operating_margin")
    gm_now = snapshot.ratio(last.period_label, "gross_margin")
    gm_prev = snapshot.ratio(prev.period_label, "gross_margin")
    deltas = []
    if om_now is not None and om_prev is not None:
        deltas.append(("operating_margin", om_now - om_prev))
    if gm_now is not None and gm_prev is not None:
        deltas.append(("gross_margin", gm_now - gm_prev))
    if not deltas:
        return None
    worst_metric, worst_delta = min(deltas, key=lambda t: t[1])
    if worst_delta >= -settings.margin_decline_threshold_pts:
        return None
    score = _scale(-worst_delta, settings.margin_decline_threshold_pts, 6.0)
    severity = severity_from_score(score)
    parts = []
    if gm_now is not None and gm_prev is not None:
        parts.append(f"gross margin {gm_prev:.1f}% -> {gm_now:.1f}%")
    if om_now is not None and om_prev is not None:
        parts.append(f"operating margin {om_prev:.1f}% -> {om_now:.1f}%")
    return DetectedRisk(
        category="margin", title="Margin compression",
        severity=severity, score=round(score, 1),
        explanation=f"{worst_metric.replace('_', ' ').title()} declined {abs(worst_delta):.1f} pts "
                    f"from {prev.period_label} to {last.period_label} ({'; '.join(parts)}).",
        why_it_matters="Margins contracting while revenue grows suggests pricing or cost pressure.",
        potential_impact="Reduced earnings power and less room to absorb cost inflation.",
        recommendation="Investigate input-cost inflation, pricing actions and product mix shifts.",
        confidence="medium",
        detected_signals={"gross_margin_delta_pts": round((gm_now - gm_prev), 2) if gm_now is not None and gm_prev is not None else None,
                          "operating_margin_delta_pts": round((om_now - om_prev), 2) if om_now is not None and om_prev is not None else None},
        evidence_hint_metric="gross_profit", evidence_period=last.period_label,
    )


def rule_interest_burden(snapshot: FinancialSnapshot, settings: Settings) -> DetectedRisk | None:
    latest = snapshot.latest
    if latest is None:
        return None
    interest = latest.values.get("interest_expense")
    ebitda = latest.values.get("ebitda")
    if not interest or not ebitda:
        return None
    burden = interest / ebitda
    if burden < settings.interest_to_ebitda_threshold:
        return None
    score = _scale(burden, settings.interest_to_ebitda_threshold, 0.6)
    severity = severity_from_score(score)
    return DetectedRisk(
        category="financial", title="Rising interest burden",
        severity=severity, score=round(score, 1),
        explanation=f"Interest expense equals {burden:.0%} of EBITDA in {latest.period_label}.",
        why_it_matters="A growing share of operating profit is consumed by interest.",
        potential_impact="Reduced earnings; sensitivity to rate increases and refinancing terms.",
        recommendation="Map the debt maturity wall and hedging policy; stress-test refinancing rates.",
        confidence="medium",
        detected_signals={"interest_to_ebitda": round(burden, 3)},
        evidence_hint_metric="interest_expense", evidence_period=latest.period_label,
    )


def rule_geographic_exposure(snapshot: FinancialSnapshot, settings: Settings) -> DetectedRisk | None:
    latest = snapshot.latest
    if latest is None:
        return None
    intl = latest.values.get("international_revenue_pct")
    if intl is None or intl < settings.intl_revenue_threshold_pct:
        return None
    score = _scale(intl, settings.intl_revenue_threshold_pct, 70.0) * 0.5
    severity = severity_from_score(score)
    return DetectedRisk(
        category="geographic", title="Significant international revenue exposure",
        severity=severity, score=round(score, 1),
        explanation=f"International operations contributed {intl:.0f}% of revenue in {latest.period_label}.",
        why_it_matters="Cross-border revenue brings FX, regulatory and geopolitical exposure.",
        potential_impact="Currency swings and regional regulation can affect reported results.",
        recommendation="Review FX hedging policy and country-level revenue split.",
        confidence="medium",
        detected_signals={"international_revenue_pct": intl},
        evidence_hint_metric="international_revenue_pct", evidence_period=latest.period_label,
    )


ALL_RULES = [
    rule_leverage,
    rule_customer_concentration,
    rule_liquidity,
    rule_cash_conversion,
    rule_margin_compression,
    rule_interest_burden,
    rule_geographic_exposure,
]


def run_risk_engine(snapshot: FinancialSnapshot, settings: Settings) -> list[DetectedRisk]:
    risks = []
    for rule in ALL_RULES:
        try:
            risk = rule(snapshot, settings)
        except Exception:  # noqa: BLE001 - one broken rule must not break analysis
            continue
        if risk is not None:
            risks.append(risk)
    risks.sort(key=lambda r: SEVERITY_ORDER[r.severity], reverse=True)
    return risks


def overall_risk_score(risks: list[DetectedRisk]) -> float:
    if not risks:
        return 0.0
    return round(sum(_SEVERITY_WEIGHT[r.severity] for r in risks) / len(risks), 1)


def risk_level_label(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 50:
        return "elevated"
    if score >= 25:
        return "moderate"
    return "low"


def risks_from_rows(rows) -> list:
    """Adapt persisted Risk ORM rows to the DetectedRisk interface used by scoring."""

    class _RowAdapter:
        def __init__(self, row) -> None:
            self.category = row.category
            self.title = row.title
            self.severity = RiskSeverity(row.severity)
            self.score = row.score
            self.explanation = row.explanation
            self.detected_signals = row.detected_signals or {}

    return [_RowAdapter(r) for r in rows]
