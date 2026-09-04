"""Evidence-grounded management-question generation from detected risks/opportunities."""
from __future__ import annotations

from app.services.opportunity.engine import DetectedOpportunity
from app.services.risk.engine import DetectedRisk

QUESTION_TEMPLATES: dict[str, list[dict]] = {
    "customer_concentration": [
        {"q": "What percentage of revenue is expected to come from the top three customers next year?",
         "r": "Quantifies forward concentration risk vs the reported {signals[top3_customer_revenue_pct]:.0f}% share.", "p": "high"},
        {"q": "How renewable are the contracts with the top three customers, and what are the termination clauses?",
         "r": "Contract durability determines how sticky concentrated revenue is.", "p": "high"},
        {"q": "What protections exist against customer loss (switching costs, exclusivity, LTAs)?",
         "r": "Tests mitigation of the reported concentration.", "p": "medium"},
    ],
    "leverage": [
        {"q": "What caused the increase in debt, and how was the proceeds deployed?",
         "r": "Links borrowing to value-creating uses.", "p": "high"},
        {"q": "What is the debt repayment schedule and maturity profile?",
         "r": "Identifies refinancing risk from the {signals[debt_growth_pct]:.0f}% debt increase.", "p": "high"},
        {"q": "What covenant restrictions apply to the credit facilities?",
         "r": "Covenants can constrain strategy precisely when performance weakens.", "p": "medium"},
        {"q": "How does management expect to fund repayment - FCF, refinancing or asset sales?",
         "r": "Tests repayment credibility.", "p": "medium"},
    ],
    "margin": [
        {"q": "What drove the margin decline, and which components are recoverable?",
         "r": "Separates structural from temporary cost pressure.", "p": "high"},
        {"q": "What pricing actions or productivity programs are planned to restore margins?",
         "r": "Tests management's margin-recovery plan.", "p": "medium"},
    ],
    "cash_flow": [
        {"q": "Why is operating cash flow lagging reported net income?",
         "r": "Quality-of-earnings follow-up on weak cash conversion.", "p": "high"},
        {"q": "What is the working-capital plan (receivables, inventory) for the next 12 months?",
         "r": "Working capital is the usual cash-conversion culprit.", "p": "medium"},
    ],
    "liquidity": [
        {"q": "What committed credit facilities are in place and what are their terms?",
         "r": "Backstop for the thin liquidity position.", "p": "high"},
    ],
    "financial": [
        {"q": "What is the interest-rate hedging policy on outstanding debt?",
         "r": "Rate sensitivity of the rising interest burden.", "p": "medium"},
    ],
    "geographic": [
        {"q": "What share of international revenue is hedged, and in which currencies?",
         "r": "Quantifies FX exposure from the {signals[international_revenue_pct]:.0f}% international share.", "p": "medium"},
        {"q": "Which regulatory regimes materially affect international operations?",
         "r": "Compliance risk scales with geographic footprint.", "p": "low"},
    ],
}

OPPORTUNITY_TEMPLATES: dict[str, list[dict]] = {
    "revenue_growth": [
        {"q": "What are the assumptions behind the revenue growth outlook (volume vs price vs mix)?",
         "r": "Grounds the growth thesis in drivers.", "p": "medium"},
    ],
    "international_expansion": [
        {"q": "Which geographies are prioritized for expansion and with what investment plan?",
         "r": "Tests execution plan behind the rising international share.", "p": "medium"},
    ],
    "rd_investment": [
        {"q": "What is the pipeline from the increased R&D spend, and when does it reach revenue?",
         "r": "Links R&D growth to future returns.", "p": "low"},
    ],
}


def generate_questions(risks: list[DetectedRisk],
                       opportunities: list[DetectedOpportunity]) -> list[dict]:
    out: list[dict] = []
    for risk in risks:
        for tpl in QUESTION_TEMPLATES.get(risk.category, []):
            try:
                question = tpl["q"].format(signals=risk.detected_signals)
                rationale = tpl["r"].format(signals=risk.detected_signals)
            except (KeyError, IndexError, ValueError):
                question, rationale = tpl["q"], tpl["r"]
            out.append({"topic": risk.category, "question": question,
                        "rationale": rationale, "priority": tpl["p"]})
    for opp in opportunities:
        for tpl in OPPORTUNITY_TEMPLATES.get(opp.category, []):
            try:
                question = tpl["q"].format(signals=opp.signals)
                rationale = tpl["r"].format(signals=opp.signals)
            except (KeyError, IndexError, ValueError):
                question, rationale = tpl["q"], tpl["r"]
            out.append({"topic": opp.category, "question": question,
                        "rationale": rationale, "priority": tpl["p"]})
    priority_order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda item: priority_order.get(item["priority"], 3))
    return out
