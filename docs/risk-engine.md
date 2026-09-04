# Risk & opportunity engines

## Design principle

Detection is **deterministic**; the LLM (when configured) only polishes explanations. Every rule yields the same structured finding regardless of AI availability:

```
category, title, severity(low|medium|high|critical), score(0-100),
signals[{metric, value, threshold, detail}],
explanation, impact, confidence,
evidence[{document, page, quote}],
follow_ups[], what_we_found, why_it_matters, potential_impact, what_to_investigate
```

## Risk rule families (~17 categories)

| Category | Trigger (deterministic) |
|---|---|
| Leverage / indebtedness | debt growth ≫ revenue growth; D/E or Debt/EBITDA above threshold |
| Liquidity | current or quick ratio below threshold |
| Cash conversion | negative OCF with positive net income |
| Margin pressure | gross/operating margin decline beyond tolerance |
| Customer concentration | top-customer share above threshold (default 30%) |
| Supplier concentration | disclosed dependency in text |
| Interest rate exposure | floating-rate debt disclosures, weak coverage |
| FX exposure | material international revenue share |
| Working capital | receivables/inventory growing faster than revenue |
| Capex intensity | capex/revenue spikes |
| Covenant / refinancing | new term loans, refinancing language |
| Execution / expansion risk | large in-flight projects |
| Regulatory / compliance | regulatory keywords with context |
| Cybersecurity | disclosed incidents or heavy reliance disclosures |
| Key person / governance | board turnover, audit qualifications |
| Competitive pressure | market share loss language |
| Disclosure consistency | contradictions between documents |

Severity scales with distance from threshold; `score` is computed from signal magnitudes — no randomness, no LLM scoring.

Each finding is persisted with **evidence rows** (`risk_evidence` → document + page + quote), powering the citation badges in the UI and the report.

## Scorecards

Five 0–100 scores aggregate category scores with fixed weights: Overall Risk, Financial Health, Growth Potential, Operational Risk, Governance Risk. Bands: `low (<25) / moderate / elevated / high (≥60)` — labels shown next to every score.

## Opportunity engine (~10 families)

Revenue momentum, margin expansion, backlog/demand signals, R&D pipeline, international expansion, capacity investment, pricing power, balance-sheet capacity, efficiency programs, ESG/product mix. Same evidence-backed structure, confidence labels, and follow-ups.

## Cross-document inconsistency detection

Claims in narrative documents (investor decks, press releases) are compared to extracted reported values from filings. On mismatch the system records a finding phrased politely:

> "Potential inconsistency detected. Further investigation recommended."

with both claims quoted side-by-side and linked to their pages.

## Management questions

Generated from the top risks/opportunities: each question carries the rationale ("because …") and links to the underlying evidence, so analysts can walk into a management meeting with a grounded agenda.
