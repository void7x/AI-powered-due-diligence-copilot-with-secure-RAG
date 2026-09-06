"use client";

import { useMemo, useState } from "react";
import { Card, CardHeader, EmptyState, ErrorState, LoadingState, Select, Table } from "@/components/ui";
import { FinancialChart } from "@/components/FinancialChart";
import { useApiData } from "@/hooks/useApi";
import { fmtDelta, fmtMoney, fmtNumber, fmtPct, titleCase } from "@/lib/format";
import type { Changes, Financials } from "@/types";

const CHARTS: { title: string; subtitle: string; series: { key: string; label: string }[]; money?: boolean }[] = [
  { title: "Revenue", subtitle: "Total revenue per fiscal period", series: [{ key: "revenue", label: "Revenue" }], money: true },
  { title: "EBITDA", subtitle: "Earnings before interest, taxes, D&A", series: [{ key: "ebitda", label: "EBITDA" }], money: true },
  { title: "Net income", subtitle: "Reported net income", series: [{ key: "net_income", label: "Net income" }], money: true },
  { title: "Margins", subtitle: "Gross / operating / net margin (%)", series: [
      { key: "gross_margin", label: "Gross" }, { key: "operating_margin", label: "Operating" }, { key: "net_margin", label: "Net" }] },
  { title: "Debt & cash", subtitle: "Total debt vs cash", series: [{ key: "debt", label: "Total debt" }, { key: "cash", label: "Cash" }], money: true },
  { title: "Cash flow", subtitle: "Operating vs free cash flow", series: [{ key: "operating_cash_flow", label: "OCF" }, { key: "free_cash_flow", label: "FCF" }], money: true },
];

export default function FinancialsPage({ params }: { params: { id: string } }) {
  const companyId = params.id;
  const { data, error, loading, refresh } = useApiData<Financials>(`/api/companies/${companyId}/financials`);
  const periods = data?.periods.map((p) => p.period_label) ?? [];
  const [base, setBase] = useState<string>("");
  const [target, setTarget] = useState<string>("");

  const effectiveBase = base || (periods.length >= 2 ? periods[periods.length - 2] : "");
  const effectiveTarget = target || (periods.length ? periods[periods.length - 1] : "");

  const changesQs = effectiveBase && effectiveTarget && effectiveBase !== effectiveTarget
    ? `base=${effectiveBase}&target=${effectiveTarget}` : null;
  const { data: changes } = useApiData<Changes>(
    changesQs ? `/api/companies/${companyId}/financials/changes?${changesQs}` : null, [changesQs]);

  const chartData = useMemo(
    () => (data?.trends ?? []).map((t) => ({ period: t.period_label, ...t.values })),
    [data]);

  const latest = data?.periods[data.periods.length - 1];
  const previous = data && data.periods.length >= 2 ? data.periods[data.periods.length - 2] : null;
  const latestRevenue = latest?.metrics.revenue ?? null;
  const latestEbitda = latest?.metrics.ebitda ?? null;
  const latestFcf = latest?.metrics.free_cash_flow ?? null;
  const latestMargin = latest?.ratios.operating_margin ?? null;
  const revenueDelta = latestRevenue != null && previous?.metrics.revenue != null && previous.metrics.revenue !== 0
    ? ((latestRevenue - previous.metrics.revenue) / Math.abs(previous.metrics.revenue)) * 100 : null;
  const debtToEbitda = latest?.ratios.debt_to_ebitda ?? null;

  if (loading) return <LoadingState label="Loading financials…" />;
  if (error) return <ErrorState message={error} retry={refresh} />;
  if (!data || data.periods.length === 0) {
    return <EmptyState title="No financial data yet"
      hint="Upload annual reports or financial statements and process them — key metrics are extracted automatically with page-level citations." />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Financial health at a glance" subtitle={`Latest reported period: ${latest?.period_label ?? "—"}`} />
        <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5">
          <Kpi label="Revenue" value={fmtMoney(latestRevenue)} delta={revenueDelta == null ? null : fmtDelta(revenueDelta)} />
          <Kpi label="EBITDA" value={fmtMoney(latestEbitda)} />
          <Kpi label="Operating margin" value={fmtPct(latestMargin)} />
          <Kpi label="Free cash flow" value={fmtMoney(latestFcf)} />
          <Kpi label="Debt / EBITDA" value={fmtNumber(debtToEbitda, 2)} />
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {CHARTS.map((c) => (
          <Card key={c.title}>
            <CardHeader title={c.title} subtitle={c.subtitle} />
            <div className="p-4">
              <FinancialChart data={chartData} height={220}
                series={c.series.map((s) => ({ ...s, format: c.money ? fmtMoney : undefined }))} />
            </div>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader title="Ratios by period" subtitle="Deterministic Python calculations — never LLM-generated" />
        <Table head={["Ratio", ...data.periods.map((p) => p.period_label)]}>
          {RATIO_ROWS.map(({ key, label, fmt }) => (
            <tr key={key} className="hover:bg-slate-50/60">
              <td className="td font-medium text-slate-700">{label}</td>
              {data.periods.map((p) => (
                <td key={p.period_label} className="td text-right tabular-nums">
                  {fmt((p.ratios[key] ?? null) as number | null)}
                </td>
              ))}
            </tr>
          ))}
        </Table>
      </Card>

      <Card>
        <CardHeader title="What changed?" subtitle="Compare two fiscal periods" />
        <div className="flex items-end gap-3 border-b border-slate-100 px-5 py-3">
          <div>
            <label className="label" htmlFor="base-period">From</label>
            <Select id="base-period" className="w-36" value={effectiveBase} onChange={(e) => setBase(e.target.value)}>
              {periods.map((p) => <option key={p} value={p}>{p}</option>)}
            </Select>
          </div>
          <span className="pb-2 text-slate-400">→</span>
          <div>
            <label className="label" htmlFor="target-period">To</label>
            <Select id="target-period" className="w-36" value={effectiveTarget} onChange={(e) => setTarget(e.target.value)}>
              {periods.map((p) => <option key={p} value={p}>{p}</option>)}
            </Select>
          </div>
        </div>
        {changes && (
          <Table head={["Metric", effectiveBase, effectiveTarget, "Change", "Reading"]}>
            {changes.items.map((i) => (
              <tr key={i.metric} className="hover:bg-slate-50/60">
                <td className="td font-medium text-slate-700">{i.label}</td>
                <td className="td text-right tabular-nums">{i.delta_pts != null ? fmtPct(i.from_value) : fmtMoney(i.from_value)}</td>
                <td className="td text-right tabular-nums">{i.delta_pts != null ? fmtPct(i.to_value) : fmtMoney(i.to_value)}</td>
                <td className={`td text-right font-medium tabular-nums ${
                  i.sentiment === "positive" ? "text-emerald-600" : i.sentiment === "negative" ? "text-red-600" : "text-slate-500"}`}>
                  {i.delta_pct != null ? fmtDelta(i.delta_pct) : i.delta_pts != null ? fmtDelta(i.delta_pts, " pts") : "—"}
                </td>
                <td className="td text-xs text-slate-500">{titleCase(i.sentiment)}</td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}

function Kpi({ label, value, delta }: { label: string; value: string; delta?: string | null }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <div className="mt-2 flex items-baseline justify-between gap-2">
        <p className="text-xl font-bold tabular-nums text-slate-900">{value}</p>
        {delta && <span className="text-xs font-semibold text-emerald-600">{delta}</span>}
      </div>
    </div>
  );
}

const RATIO_ROWS: { key: string; label: string; fmt: (v: number | null) => string }[] = [
  { key: "gross_margin", label: "Gross margin", fmt: fmtPct },
  { key: "operating_margin", label: "Operating margin", fmt: fmtPct },
  { key: "net_margin", label: "Net margin", fmt: fmtPct },
  { key: "ebitda_margin", label: "EBITDA margin", fmt: fmtPct },
  { key: "fcf_margin", label: "FCF margin", fmt: fmtPct },
  { key: "current_ratio", label: "Current ratio", fmt: (v) => fmtNumber(v, 2) },
  { key: "quick_ratio", label: "Quick ratio", fmt: (v) => fmtNumber(v, 2) },
  { key: "debt_to_equity", label: "Debt / equity", fmt: (v) => fmtNumber(v, 2) },
  { key: "debt_to_ebitda", label: "Debt / EBITDA", fmt: (v) => fmtNumber(v, 2) },
  { key: "roe", label: "ROE", fmt: fmtPct },
  { key: "roa", label: "ROA", fmt: fmtPct },
  { key: "ocf_to_net_income", label: "OCF / net income", fmt: (v) => fmtNumber(v, 2) },
  { key: "interest_coverage_ebitda", label: "EBITDA / interest", fmt: (v) => fmtNumber(v, 1) },
  { key: "rnd_intensity", label: "R&D intensity", fmt: fmtPct },
];
