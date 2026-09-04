"""'What changed?' period-over-period comparison service."""
from __future__ import annotations

from app.schemas.finance import ChangeItemOut, ChangesOut
from app.services.finance.metrics import pct_change, safe_div
from app.services.finance.service import FinancialSnapshot

_ITEMS = [
    ("Revenue", "total_revenue", "value"),
    ("Net income", "net_income", "value"),
    ("EBITDA", "ebitda", "value"),
    ("Debt", "total_debt", "value"),
    ("Cash", "cash", "value"),
    ("Operating cash flow", "operating_cash_flow", "value"),
    ("Free cash flow", "free_cash_flow", "value"),
    ("Gross margin", "gross_margin", "ratio"),
    ("Operating margin", "operating_margin", "ratio"),
    ("Net margin", "net_margin", "ratio"),
    ("Current ratio", "current_ratio", "ratio"),
    ("Debt-to-equity", "debt_to_equity", "ratio"),
]
# metrics where an increase is BAD (sentiment flips)
_BAD_UP = {"total_debt", "debt_to_equity"}


def compute_changes(snapshot: FinancialSnapshot, base_label: str, target_label: str) -> ChangesOut:
    base = next((p for p in snapshot.periods if p.period_label == base_label), None)
    target = next((p for p in snapshot.periods if p.period_label == target_label), None)
    items: list[ChangeItemOut] = []
    if base is None or target is None:
        return ChangesOut(from_period=base_label, to_period=target_label, items=[],
                          narrative="One of the requested periods has no financial data.")
    for label, metric, kind in _ITEMS:
        if kind == "value":
            old, new = base.values.get(metric), target.values.get(metric)
            delta_pct = pct_change(old, new)
            delta = None if delta_pct is None else round(delta_pct * 100, 1)
            from_value, to_value = old, new
        else:
            old, new = snapshot.ratio(base.period_label, metric), snapshot.ratio(target.period_label, metric)
            delta = None if old is None or new is None else round(new - old, 2)
            from_value, to_value = old, new
        if from_value is None and to_value is None:
            continue
        direction = "flat"
        if delta is not None and delta != 0:
            direction = "up" if delta > 0 else "down"
        sentiment = "neutral"
        if delta not in (None, 0):
            bad = metric in _BAD_UP
            positive = (delta > 0) != bad
            sentiment = "positive" if positive else "negative"
        items.append(ChangeItemOut(
            label=label, metric=metric, from_value=from_value, to_value=to_value,
            delta_pct=delta if kind == "value" else None,
            delta_pts=delta if kind == "ratio" else None,
            direction=direction, sentiment=sentiment))
    changed = [i for i in items if i.direction != "flat"]
    narrative = (f"Comparing {base_label} -> {target_label}: "
                 + "; ".join(f"{i.label} {'+' if (i.delta_pct or i.delta_pts or 0) > 0 else ''}"
                             f"{i.delta_pct if i.delta_pct is not None else i.delta_pts}"
                             f"{'%' if i.delta_pct is not None else ' pts'}" for i in changed[:6])
                 + ".") if changed else "No material changes detected between the selected periods."
    return ChangesOut(from_period=base_label, to_period=target_label, items=items, narrative=narrative)
