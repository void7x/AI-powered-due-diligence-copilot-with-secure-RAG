"""Deterministic financial calculations: growth, CAGR, margins, ratios, edge cases."""
import pytest

from app.services.finance.metrics import (
    PeriodFacts, build_facts, cagr, compute_cagrs, compute_period_ratios,
    pct_change, revenue_growth, safe_div,
)
from app.services.finance.service import financial_health_score, growth_potential_score


def _facts():
    return build_facts(
        {
            "FY2023": {"total_revenue": 410.2, "net_income": 39.8, "total_debt": 142.0,
                        "current_assets": 210.5, "current_liabilities": 131.2, "inventory": 58.3,
                        "total_assets": 402.7, "shareholders_equity": 197.4,
                        "ebitda": 70.4, "operating_income": 61.5, "gross_profit": 164.1,
                        "operating_cash_flow": 62.4, "free_cash_flow": 43.5},
            "FY2024": {"total_revenue": 520.8, "net_income": 55.2, "total_debt": 175.3,
                        "current_assets": 238.9, "current_liabilities": 146.3, "inventory": 66.1,
                        "total_assets": 461.5, "shareholders_equity": 215.3,
                        "ebitda": 89.1, "operating_income": 83.3, "gross_profit": 208.3,
                        "operating_cash_flow": 71.8, "free_cash_flow": 47.2},
            "FY2025": {"total_revenue": 630.4, "net_income": 58.9, "total_debt": 230.1,
                        "current_assets": 261.3, "current_liabilities": 163.2, "inventory": 74.9,
                        "total_assets": 528.4, "shareholders_equity": 235.7,
                        "ebitda": 97.8, "operating_income": 88.3, "gross_profit": 239.2,
                        "operating_cash_flow": 74.2, "free_cash_flow": 44.4},
        },
        {"FY2023": 2023, "FY2024": 2024, "FY2025": 2025},
    )


def test_safe_div_handles_zero_and_none():
    assert safe_div(10, 2) == 5.0
    assert safe_div(10, 0) is None
    assert safe_div(None, 2) is None
    assert safe_div(10, None) is None


def test_pct_change_handles_zero_base():
    assert pct_change(0, 10) is None
    assert pct_change(100, 150) == pytest.approx(0.5)
    assert pct_change(-100, -50) == pytest.approx(0.5)


def test_cagr():
    assert cagr(100, 121, 2) == pytest.approx(0.10, abs=1e-6)
    assert cagr(0, 100, 2) is None
    assert cagr(100, 100, 0) is None
    assert cagr(None, 100, 2) is None


def test_ratios_fy2025():
    ratios = compute_period_ratios(_facts()[2])
    assert ratios["gross_margin"] == pytest.approx(37.94, abs=0.01)
    assert ratios["operating_margin"] == pytest.approx(14.01, abs=0.01)
    assert ratios["current_ratio"] == pytest.approx(1.6009, abs=0.001)
    assert ratios["debt_to_equity"] == pytest.approx(0.9762, abs=0.001)
    assert ratios["debt_to_ebitda"] == pytest.approx(2.3528, abs=0.001)
    assert ratios["roe"] == pytest.approx(24.99, abs=0.05)
    assert ratios["quick_ratio"] == pytest.approx(1.1419, abs=0.001)


def test_revenue_growth_series():
    growth = revenue_growth(_facts())
    assert growth["FY2023->FY2024"] == pytest.approx(26.96, abs=0.05)
    assert growth["FY2024->FY2025"] == pytest.approx(21.04, abs=0.05)


def test_cagr_series():
    cagrs = compute_cagrs(_facts())
    assert cagrs["total_revenue"] == pytest.approx(23.99, abs=0.05)


def test_quick_ratio_edge_cases():
    from app.services.finance.metrics import quick_ratio
    assert quick_ratio(100, 40, 50) == pytest.approx(1.2)
    assert quick_ratio(100, None, 50) == pytest.approx(2.0)
    assert quick_ratio(None, 10, 50) is None
    assert quick_ratio(100, 40, 0) is None


def test_scores_deterministic():
    facts = _facts()
    snapshot = type("S", (), {"periods": facts, "latest": facts[-1],
                               "ratios_by_period": {f.period_label: compute_period_ratios(f) for f in facts},
                               "growth": revenue_growth(facts), "cagrs": compute_cagrs(facts),
                               "ratio": None})()
    snapshot.ratio = lambda p, n: snapshot.ratios_by_period.get(p, {}).get(n)
    health, health_level = financial_health_score(snapshot)
    growth, growth_level = growth_potential_score(snapshot)
    assert 0 <= health <= 100 and health_level in ("strong", "adequate", "weak")
    assert 0 <= growth <= 100 and growth_level in ("high", "moderate", "limited")
    # identical input -> identical output
    assert financial_health_score(snapshot) == (health, health_level)
