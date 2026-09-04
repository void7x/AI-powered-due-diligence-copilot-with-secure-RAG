"""Risk engine rules: leverage, liquidity, concentration, cash conversion, margins."""
import pytest

from app.core.config import Settings
from app.services.finance.service import FinancialSnapshot, load_snapshot  # noqa: F401
from app.services.finance.metrics import build_facts, compute_period_ratios, revenue_growth, compute_cagrs
from app.services.risk.engine import (
    overall_risk_score, risk_level_label, rule_cash_conversion, rule_customer_concentration,
    rule_leverage, rule_liquidity, rule_margin_compression, run_risk_engine,
)


def _snapshot(values_by_period: dict, years: dict) -> FinancialSnapshot:
    facts = build_facts(values_by_period, years)
    return FinancialSnapshot(
        periods=facts,
        ratios_by_period={f.period_label: compute_period_ratios(f) for f in facts},
        growth=revenue_growth(facts), cagrs=compute_cagrs(facts), metric_sources={},
    )


SETTINGS = Settings(secret_key="test", database_url="sqlite://")


def test_leverage_rule_fires_when_debt_outpaces_revenue():
    snapshot = _snapshot(
        {"FY2024": {"total_revenue": 520.8, "total_debt": 175.3, "ebitda": 89.1},
         "FY2025": {"total_revenue": 630.4, "total_debt": 230.1, "ebitda": 97.8}},
        {"FY2024": 2024, "FY2025": 2025})
    risk = rule_leverage(snapshot, SETTINGS)
    assert risk is not None
    assert risk.category == "leverage"
    assert risk.detected_signals["debt_growth_pct"] == pytest.approx(31.26, abs=0.05)
    assert risk.detected_signals["revenue_growth_pct"] == pytest.approx(21.04, abs=0.05)
    assert risk.detected_signals["debt_to_ebitda"] == pytest.approx(2.3528, abs=0.001)
    assert risk.severity.value in ("medium", "high")


def test_leverage_rule_scores_with_absolute_leverage():
    low = _snapshot(
        {"FY2024": {"total_revenue": 520.8, "total_debt": 175.3, "ebitda": 200.0},
         "FY2025": {"total_revenue": 630.4, "total_debt": 230.1, "ebitda": 240.0}},
        {"FY2024": 2024, "FY2025": 2025})
    high = _snapshot(
        {"FY2024": {"total_revenue": 520.8, "total_debt": 175.3, "ebitda": 80.0},
         "FY2025": {"total_revenue": 630.4, "total_debt": 330.1, "ebitda": 95.0}},
        {"FY2024": 2024, "FY2025": 2025})
    assert rule_leverage(high, SETTINGS).score > rule_leverage(low, SETTINGS).score


def test_leverage_rule_quiet_when_debt_grows_slower():
    snapshot = _snapshot(
        {"FY2024": {"total_revenue": 500.0, "total_debt": 100.0},
         "FY2025": {"total_revenue": 600.0, "total_debt": 105.0}},
        {"FY2024": 2024, "FY2025": 2025})
    assert rule_leverage(snapshot, SETTINGS) is None


def test_customer_concentration_rule_threshold():
    snapshot = _snapshot(
        {"FY2025": {"top3_customer_revenue_pct": 44.0, "total_revenue": 630.4}},
        {"FY2025": 2025})
    risk = rule_customer_concentration(snapshot, SETTINGS)
    assert risk is not None and risk.severity.value in ("high", "critical")

    borderline = _snapshot({"FY2025": {"top3_customer_revenue_pct": 33.0}}, {"FY2025": 2025})
    mild = rule_customer_concentration(borderline, SETTINGS)
    assert mild is not None and mild.severity.value in ("low", "medium")

    low = _snapshot({"FY2025": {"top3_customer_revenue_pct": 12.0}}, {"FY2025": 2025})
    assert rule_customer_concentration(low, SETTINGS) is None


def test_liquidity_rule():
    weak = _snapshot(
        {"FY2025": {"current_assets": 120.0, "current_liabilities": 150.0, "inventory": 40.0}},
        {"FY2025": 2025})
    risk = rule_liquidity(weak, SETTINGS)
    assert risk is not None and risk.category == "liquidity"

    healthy = _snapshot(
        {"FY2025": {"current_assets": 300.0, "current_liabilities": 150.0, "inventory": 50.0}},
        {"FY2025": 2025})
    assert rule_liquidity(healthy, SETTINGS) is None


def test_cash_conversion_rule_negative_ocf_positive_ni():
    snapshot = _snapshot(
        {"FY2024": {"net_income": 45.0, "operating_cash_flow": 40.0},
         "FY2025": {"net_income": 50.0, "operating_cash_flow": -20.0}},
        {"FY2024": 2024, "FY2025": 2025})
    risk = rule_cash_conversion(snapshot, SETTINGS)
    assert risk is not None
    assert "negative" in risk.explanation.lower()
    assert risk.severity.value in ("high", "critical")


def test_cash_conversion_quiet_when_conversion_healthy():
    snapshot = _snapshot(
        {"FY2024": {"net_income": 50.0, "operating_cash_flow": 55.0},
         "FY2025": {"net_income": 60.0, "operating_cash_flow": 70.0}},
        {"FY2024": 2024, "FY2025": 2025})
    assert rule_cash_conversion(snapshot, SETTINGS) is None


def test_margin_compression_rule():
    snapshot = _snapshot(
        {"FY2024": {"total_revenue": 520.8, "gross_profit": 208.3, "operating_income": 83.3},
         "FY2025": {"total_revenue": 630.4, "gross_profit": 239.2, "operating_income": 88.3}},
        {"FY2024": 2024, "FY2025": 2025})
    risk = rule_margin_compression(snapshot, SETTINGS)
    assert risk is not None
    assert risk.category == "margin"
    assert risk.detected_signals["gross_margin_delta_pts"] == pytest.approx(-2.05, abs=0.1)


def test_overall_score_and_level():
    assert overall_risk_score([]) == 0.0
    assert risk_level_label(80) == "high"
    assert risk_level_label(10) == "low"


def test_engine_never_crashes_on_partial_data():
    snapshot = _snapshot({"FY2025": {"total_revenue": 10.0}}, {"FY2025": 2025})
    risks = run_risk_engine(snapshot, SETTINGS)
    assert isinstance(risks, list)
