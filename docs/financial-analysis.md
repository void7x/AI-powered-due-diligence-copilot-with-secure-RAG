# Financial intelligence

## Extraction (never trusted blindly)

During `ANALYZING`, the finance extractor scans pages and normalized tables for a set of core financial metrics, including revenue, gross profit, operating income, EBITDA, net income, cash, liquidity inputs, debt, equity, operating cash flow, capex, free cash flow, receivables, inventory, interest expense and R&D expense.

- Numbers are matched with label context (income statement / balance sheet / cash flow sections), with currency and unit metadata captured where available.
- Fiscal year is resolved from document metadata or statement context.
- **Uncertain matches are flagged, not guessed**; values are stored in financial-period records with source-page provenance.
- Currencies are kept with each period. Comparisons across incompatible currencies are not silently averaged.

## Ratios — deterministic Python only

Derived numbers are computed by the finance service's pure deterministic functions and covered by `tests/test_finance.py`. The LLM is never asked to perform financial arithmetic.

Implemented measures include:

- Growth: YoY revenue growth, multi-period CAGR
- Margins: gross, operating, EBITDA, net, FCF
- Liquidity: current ratio, quick ratio
- Leverage: debt/equity, debt/EBITDA, EBITDA/interest coverage
- Returns: ROA, ROE
- Cash quality: OCF/net income and OCF − capex = FCF
- R&D intensity

Division-by-zero and missing inputs yield `None` (shown as “—” in the UI), never `0` or a fabricated number.

## Trend & compare endpoints

- `GET /api/companies/{id}/financials` → periods, ratios and trend series for charts.
- `GET /api/companies/{id}/financials/changes?base=FY2024&target=FY2025` → per-metric changes with direction, magnitude and coarse sentiment.

## Charts

The frontend plots server-computed series such as revenue/EBITDA/net income, margins, debt vs cash, and OCF vs FCF. Formatting is presentation-only; financial calculations remain backend-owned.
