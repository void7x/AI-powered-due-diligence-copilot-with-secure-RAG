# Financial intelligence

## Extraction (never trusted blindly)

During `ANALYZING`, the finance extractor scans **pages** and **normalized tables** for ~18 core metrics:

`total_revenue, cogs, gross_profit, operating_income, ebitda, net_income, cash, current_assets, current_liabilities, total_assets, total_liabilities, total_debt, shareholders_equity, operating_cash_flow, capex, free_cash_flow, accounts_receivable, inventory, interest_expense, rnd_expense`

- Numbers are matched with label context (income statement / balance sheet / cash flow sections), currency and unit (thousands/millions) captured, and fiscal year resolved from the document metadata or the statement header.
- **Uncertain matches are flagged, not guessed**; values are stored per `financial_periods` row with the source page for citation.
- Currencies are never silently mixed: periods carry currency, and comparisons across differing currencies are refused (flagged) rather than averaged.

## Ratios — deterministic Python only

All derived numbers are computed in `app/services/finance/ratios.py` (pure functions, unit-tested in `tests/test_finance.py`). The LLM is **never** asked to do math. Implemented metrics:

- Growth: YoY revenue growth, 2-year CAGR
- Margins: gross, operating, EBITDA, net, FCF
- Liquidity: current ratio, quick ratio
- Leverage: debt/equity, debt/EBITDA, EBITDA/interest coverage
- Returns: ROA, ROE
- Cash quality: OCF/net income, OCF−capex = FCF
- R&D intensity

Division-by-zero and missing inputs yield `None` (shown as "—" in UI), never `0` or a fabricated number.

## Trend & compare endpoints

- `GET /api/companies/{id}/financials` → periods, ratios per period, trend series for charts.
- `GET /api/companies/{id}/financials/changes?base=FY2024&target=FY2025` → "what changed": per-metric deltas with magnitude and a coarse sentiment classification — the period-compare feature.

## Charts

The frontend plots only server-computed series (Recharts): revenue/EBITDA/net income, margins, debt vs cash, OCF vs FCF. Tooltips format with the same units the backend stored (e.g. `€m`).
