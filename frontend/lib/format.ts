export function fmtNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtMoney(value: number | null | undefined, unit = "million"): string {
  if (value === null || value === undefined) return "—";
  const symbol = "$";
  if (unit === "billion") return `${symbol}${fmtNumber(value, 1)}B`;
  if (unit === "thousand") return `${symbol}${fmtNumber(value / 1000, 1)}M`;
  return `${symbol}${fmtNumber(value, 1)}M`;
}

export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return `${value >= 0 ? "" : ""}${value.toFixed(digits)}%`;
}

export function fmtDelta(value: number | null | undefined, suffix = "%"): string {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}${suffix}`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export const DOC_TYPE_LABELS: Record<string, string> = {
  annual_report: "Annual Report", "10_k": "10-K", "10_q": "10-Q",
  earnings_report: "Earnings Report", investor_presentation: "Investor Presentation",
  financial_statement: "Financial Statements", market_report: "Market Report",
  press_release: "Press Release", other: "Other",
};
