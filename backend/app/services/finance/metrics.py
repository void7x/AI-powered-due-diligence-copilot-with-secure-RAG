"""Deterministic financial ratio calculations. Pure functions, fully tested.

The LLM is NEVER used for core calculations - these are auditable and exact.
All functions are None-safe (missing/divide-by-zero inputs return None).
"""
from __future__ import annotations

from dataclasses import dataclass, field


def safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return None


def pct_change(old: float | None, new: float | None) -> float | None:
    if old in (None, 0) or new is None:
        return None
    return (new - old) / abs(old)


def cagr(begin: float | None, end: float | None, years: float | None) -> float | None:
    if not begin or not end or not years or years <= 0 or begin <= 0 or end <= 0:
        return None
    return (end / begin) ** (1 / years) - 1


@dataclass
class PeriodFacts:
    """One fiscal period of normalized financial facts (values in one currency/unit)."""

    period_label: str
    fiscal_year: int
    values: dict[str, float] = field(default_factory=dict)

    def get(self, metric: str) -> float | None:
        return self.values.get(metric)


def build_facts(metrics_by_period: dict[str, dict[str, float]],
                years_by_period: dict[str, int]) -> list[PeriodFacts]:
    facts = [
        PeriodFacts(period_label=label, fiscal_year=years_by_period.get(label, 0), values=values)
        for label, values in metrics_by_period.items()
    ]
    facts.sort(key=lambda f: f.fiscal_year)
    return facts


def compute_period_ratios(facts: PeriodFacts) -> dict[str, float | None]:
    v = facts.values
    g = lambda m: v.get(m)  # noqa: E731
    return {
        "gross_margin": pct(safe_div(g("gross_profit"), g("total_revenue"))),
        "operating_margin": pct(safe_div(g("operating_income"), g("total_revenue"))),
        "net_margin": pct(safe_div(g("net_income"), g("total_revenue"))),
        "ebitda_margin": pct(safe_div(g("ebitda"), g("total_revenue"))),
        "fcf_margin": pct(safe_div(g("free_cash_flow"), g("total_revenue"))),
        "current_ratio": ratio(safe_div(g("current_assets"), g("current_liabilities"))),
        "quick_ratio": quick_ratio(g("current_assets"), g("inventory"), g("current_liabilities")),
        "debt_to_equity": ratio(safe_div(g("total_debt"), g("shareholders_equity"))),
        "debt_to_ebitda": ratio(safe_div(g("total_debt"), g("ebitda"))),
        "roa": pct(safe_div(g("net_income"), g("total_assets"))),
        "roe": pct(safe_div(g("net_income"), g("shareholders_equity"))),
        "ocf_to_net_income": ratio(safe_div(g("operating_cash_flow"), g("net_income"))),
        "interest_coverage_ebitda": ratio(safe_div(g("ebitda"), g("interest_expense"))),
        "rnd_intensity": pct(safe_div(g("rnd_expense"), g("total_revenue"))),
        "cash_to_debt": ratio(safe_div(g("cash"), g("total_debt"))),
    }


def ratio(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def pct(value: float | None) -> float | None:
    return None if value is None else round(value * 100, 2)


def quick_ratio(current_assets: float | None, inventory: float | None,
                current_liabilities: float | None) -> float | None:
    if current_assets is None or current_liabilities in (None, 0):
        return None
    inv = inventory or 0.0
    return ratio(safe_div(current_assets - inv, current_liabilities))


def revenue_growth(facts: list[PeriodFacts]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for prev, cur in zip(facts, facts[1:]):
        out[f"{prev.period_label}->{cur.period_label}"] = (
            None if pct_change(prev.get("total_revenue"), cur.get("total_revenue")) is None
            else round(pct_change(prev.get("total_revenue"), cur.get("total_revenue")) * 100, 2)  # type: ignore[union-attr]
        )
    return out


def compute_cagrs(facts: list[PeriodFacts]) -> dict[str, float | None]:
    if len(facts) < 2:
        return {}
    years = facts[-1].fiscal_year - facts[0].fiscal_year
    out: dict[str, float | None] = {}
    for metric in ("total_revenue", "net_income", "operating_cash_flow", "total_debt", "ebitda"):
        value = cagr(facts[0].get(metric), facts[-1].get(metric), years)
        out[metric] = None if value is None else round(value * 100, 2)
    return out
