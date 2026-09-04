"""Deterministic opportunity detection over financial facts + document signals."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.finance.service import FinancialSnapshot


@dataclass
class DetectedOpportunity:
    category: str
    title: str
    description: str
    potential_impact: str
    confidence: str = "medium"
    signals: dict = field(default_factory=dict)
    evidence_hint_metric: str = ""
    evidence_period: str = ""


def detect_opportunities(snapshot: FinancialSnapshot) -> list[DetectedOpportunity]:
    out: list[DetectedOpportunity] = []
    latest = snapshot.latest
    if latest is None or len(snapshot.periods) < 2:
        return out
    rev_cagr = snapshot.cagrs.get("total_revenue")
    if rev_cagr is not None and rev_cagr >= 10:
        out.append(DetectedOpportunity(
            category="revenue_growth", title="Strong revenue growth trajectory",
            description=f"Revenue CAGR of {rev_cagr:.1f}% across the analyzed periods "
                        f"({snapshot.periods[0].period_label}-{latest.period_label}).",
            potential_impact="Compounding top-line growth if margins stabilize.",
            confidence="high",
            signals={"revenue_cagr_pct": rev_cagr},
            evidence_hint_metric="total_revenue", evidence_period=latest.period_label,
        ))
    om_now = snapshot.ratio(latest.period_label, "operating_margin")
    om_prev = snapshot.ratio(snapshot.periods[-2].period_label, "operating_margin")
    if om_now is not None and om_prev is not None and om_now - om_prev >= 1.0:
        out.append(DetectedOpportunity(
            category="expanding_margins", title="Operating margin expansion",
            description=f"Operating margin improved from {om_prev:.1f}% to {om_now:.1f}%.",
            potential_impact="Operating leverage as revenue scales.",
            confidence="medium",
            signals={"operating_margin_delta_pts": round(om_now - om_prev, 2)},
            evidence_hint_metric="operating_income", evidence_period=latest.period_label,
        ))
    rnd_growth = None
    rnd = [p.values.get("rnd_expense") for p in snapshot.periods]
    if len(rnd) >= 2 and rnd[-2] and rnd[-1]:
        rnd_growth = (rnd[-1] - rnd[-2]) / rnd[-2] * 100
    if rnd_growth is not None and rnd_growth >= 10:
        out.append(DetectedOpportunity(
            category="rd_investment", title="Accelerating R&D investment",
            description=f"R&D spend grew {rnd_growth:.1f}% in {latest.period_label} "
                        f"({rnd[-2]:,.1f} -> {rnd[-1]:,.1f}).",
            potential_impact="Pipeline of new products could support future growth.",
            confidence="medium",
            signals={"rnd_growth_pct": round(rnd_growth, 2),
                     "rnd_intensity_pct": snapshot.ratio(latest.period_label, "rnd_intensity")},
            evidence_hint_metric="rnd_expense", evidence_period=latest.period_label,
        ))
    intl = [p.values.get("international_revenue_pct") for p in snapshot.periods]
    if len(intl) >= 2 and None not in (intl[-2], intl[-1]) and intl[-1] - intl[-2] >= 3:  # type: ignore[operator]
        out.append(DetectedOpportunity(
            category="international_expansion", title="International expansion underway",
            description=(f"International revenue share rose from {intl[-2]:.0f}% to {intl[-1]:.0f}% "
                         f"between {snapshot.periods[-2].period_label} and {latest.period_label}."),
            potential_impact="Access to larger addressable markets.",
            confidence="medium",
            signals={"international_revenue_pct": intl[-1],
                     "delta_pts": round(intl[-1] - intl[-2], 1)},  # type: ignore[operator]
            evidence_hint_metric="international_revenue_pct", evidence_period=latest.period_label,
        ))
    cash, debt = latest.values.get("cash"), latest.values.get("total_debt")
    if cash and debt and cash / debt >= 0.5:
        out.append(DetectedOpportunity(
            category="strong_cash_position", title="Healthy cash position",
            description=f"Cash of {cash:,.1f} against total debt of {debt:,.1f} "
                        f"({cash / debt:.0%}) in {latest.period_label}.",
            potential_impact="Balance-sheet capacity for bolt-on M&A or investment.",
            confidence="medium",
            signals={"cash": cash, "total_debt": debt},
            evidence_hint_metric="cash", evidence_period=latest.period_label,
        ))
    return out
