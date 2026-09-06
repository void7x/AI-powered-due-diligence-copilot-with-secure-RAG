"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, Play, ShieldAlert } from "lucide-react";
import { Button, Card, CardHeader, ErrorState, LoadingState } from "@/components/ui";
import { ScoreCard } from "@/components/ScoreCard";
import { SeverityBadge } from "@/components/SeverityBadge";
import { FinancialChart } from "@/components/FinancialChart";
import { AnalyzeProgress } from "@/components/AnalysisPanel";
import { useApiData } from "@/hooks/useApi";
import { useToast } from "@/hooks/useToast";
import { apiPost } from "@/lib/api";
import { DOC_TYPE_LABELS, fmtDate, fmtMoney } from "@/lib/format";
import type { CompanyOverview } from "@/types";

export default function CompanyOverviewPage({ params }: { params: { id: string } }) {
  const companyId = params.id;
  const { data, error, loading, refresh } = useApiData<CompanyOverview>(`/api/companies/${companyId}/overview`);
  const [jobId, setJobId] = useState<string | null>(null);
  const { toast } = useToast();

  const analyze = async () => {
    try {
      const res = await apiPost<{ job_id: string }>(`/api/companies/${companyId}/analyze`);
      setJobId(res.job_id);
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Analysis could not start");
    }
  };

  if (loading) return <LoadingState label="Loading company workspace…" />;
  if (error) return <ErrorState message={error} retry={refresh} />;
  if (!data) return null;

  const overallRisk = data.scorecards.find((s) => s.label === "Overall Risk")?.score ?? null;
  const financialHealth = data.scorecards.find((s) => s.label === "Financial Health")?.score ?? null;
  const growthPotential = data.scorecards.find((s) => s.label === "Growth Potential")?.score ?? null;
  const leadRisk = data.top_risks[0];
  const leadOpportunity = data.top_opportunities[0];
  const readinessInputs = [
    data.document_count > 0,
    data.ready_document_count === data.document_count && data.document_count > 0,
    data.last_analyzed_at != null,
    data.report_id != null,
    data.top_risks.length > 0 || data.top_opportunities.length > 0,
  ];
  const readinessScore = Math.round((readinessInputs.filter(Boolean).length / readinessInputs.length) * 100);
  const readiness = readinessScore >= 80
    ? { label: "Decision-ready", tone: "bg-emerald-100 text-emerald-700", bar: "bg-emerald-500" }
    : readinessScore >= 50
      ? { label: "Analysis in progress", tone: "bg-amber-100 text-amber-700", bar: "bg-amber-500" }
      : { label: "Needs preparation", tone: "bg-slate-100 text-slate-600", bar: "bg-slate-400" };
  const recommendation = overallRisk == null || growthPotential == null
    ? { label: "Insufficient evidence", tone: "bg-slate-100 text-slate-700", explanation: "Complete document processing and analysis before making a diligence decision." }
    : overallRisk >= 70 && growthPotential < 60
      ? { label: "Proceed with caution", tone: "bg-red-100 text-red-700", explanation: "Risk signals currently outweigh the documented growth upside." }
      : overallRisk >= 70
        ? { label: "Investigate before proceeding", tone: "bg-amber-100 text-amber-700", explanation: "The company shows meaningful upside, but elevated risk signals require validation." }
        : growthPotential >= 70 && overallRisk < 45
          ? { label: "Strong candidate for deeper diligence", tone: "bg-emerald-100 text-emerald-700", explanation: "Growth signals are strong while the current risk profile remains comparatively contained." }
          : { label: "Continue diligence", tone: "bg-blue-100 text-blue-700", explanation: "The evidence is mixed; focus the next review cycle on the leading risks and upside signals." };
  const posture = overallRisk == null
    ? "Awaiting analysis"
    : overallRisk >= 70 ? "High diligence risk"
    : overallRisk >= 45 ? "Elevated diligence risk"
    : "Lower diligence risk";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          {data.ready_document_count}/{data.document_count} documents processed
          {data.last_analyzed_at ? ` · last analyzed ${fmtDate(data.last_analyzed_at)}` : " · not analyzed yet"}
        </p>
        <div className="flex gap-2">
          <Button size="sm" onClick={analyze}><Play size={12} /> Run full due diligence</Button>
          {data.report_id && (
            <Link href={`/reports/${data.report_id}`}>
              <Button size="sm" variant="secondary">Open latest report</Button>
            </Link>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {data.scorecards.map((s) => <ScoreCard key={s.label} {...s} />)}
      </div>

      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 bg-slate-50/70 px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert size={16} className="text-navy-700" />
                <h2 className="text-sm font-semibold text-slate-900">Decision snapshot</h2>
              </div>
              <p className="mt-1 text-xs text-slate-500">A fast read on where the diligence team should focus next.</p>
            </div>
            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
              overallRisk == null ? "bg-slate-100 text-slate-600" :
              overallRisk >= 70 ? "bg-red-100 text-red-700" :
              overallRisk >= 45 ? "bg-amber-100 text-amber-700" :
              "bg-emerald-100 text-emerald-700"
            }`}>
              {posture}
            </span>
          </div>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-4">
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Financial health</p>
            <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900">
              {financialHealth == null ? "—" : `${financialHealth.toFixed(0)}/100`}
            </p>
            <p className="mt-1 text-xs text-slate-500">Balance-sheet and cash-flow strength.</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Growth potential</p>
            <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900">
              {growthPotential == null ? "—" : `${growthPotential.toFixed(0)}/100`}
            </p>
            <p className="mt-1 text-xs text-slate-500">Evidence-backed upside signals.</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Diligence readiness</p>
            <div className="mt-2 flex items-baseline justify-between gap-2">
              <p className="text-2xl font-bold tabular-nums text-slate-900">{readinessScore}%</p>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${readiness.tone}`}>{readiness.label}</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div className={`h-full rounded-full ${readiness.bar}`} style={{ width: `${readinessScore}%` }} />
            </div>
            <p className="mt-1 text-xs text-slate-500">Documents, analysis, findings, and report completeness.</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Immediate focus</p>
            {leadRisk ? (
              <Link href={`/companies/${companyId}/risks`} className="mt-2 flex items-start justify-between gap-2 text-sm font-medium text-navy-700 hover:underline">
                <span className="line-clamp-2">{leadRisk.title}</span>
                <ArrowRight size={14} className="mt-0.5 shrink-0" />
              </Link>
            ) : leadOpportunity ? (
              <Link href={`/companies/${companyId}/opportunities`} className="mt-2 flex items-start justify-between gap-2 text-sm font-medium text-navy-700 hover:underline">
                <span className="line-clamp-2">{leadOpportunity.title}</span>
                <ArrowRight size={14} className="mt-0.5 shrink-0" />
              </Link>
            ) : (
              <p className="mt-2 text-sm text-slate-500">Run analysis to identify the first diligence priority.</p>
            )}
            <p className="mt-1 text-xs text-slate-500">Start with the strongest risk signal, then validate the upside.</p>
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4 p-5">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Executive recommendation</p>
            <h2 className="mt-1 text-lg font-semibold text-slate-900">{recommendation.label}</h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-500">{recommendation.explanation}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${recommendation.tone}`}>Risk × upside synthesis</span>
        </div>
      </Card>

      <Card>
        <CardHeader title="Financial overview" subtitle="Extracted from filings — deterministic and source-cited" />
        <div className="p-4">
          {data.revenue_trend.some((p) => p.total_revenue != null) ? (
            <FinancialChart
              data={data.revenue_trend.map((p) => ({
                period: p.period, Revenue: p.total_revenue, EBITDA: p.ebitda, "Net income": p.net_income,
              }))}
              series={[
                { key: "Revenue", label: "Revenue", format: (v) => fmtMoney(v) },
                { key: "EBITDA", label: "EBITDA", format: (v) => fmtMoney(v) },
                { key: "Net income", label: "Net income", format: (v) => fmtMoney(v) },
              ]}
            />
          ) : (
            <p className="py-8 text-center text-sm text-slate-500">
              No financial data extracted yet — upload annual reports or financial statements, then run an analysis.
            </p>
          )}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Risk overview"
            action={<Link href={`/companies/${companyId}/risks`} className="text-xs font-medium text-navy-600 hover:underline">View all</Link>} />
          <ul className="divide-y divide-slate-100">
            {data.top_risks.map((r) => (
              <li key={r.id} className="px-5 py-3">
                <div className="flex items-center gap-2">
                  <SeverityBadge level={r.severity} />
                  <span className="text-sm font-medium text-slate-800">{r.title}</span>
                </div>
                <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">{r.explanation}</p>
              </li>
            ))}
            {data.top_risks.length === 0 && (
              <li className="px-5 py-6 text-center text-xs text-slate-400">No risks detected yet — run an analysis.</li>
            )}
          </ul>
        </Card>

        <Card>
          <CardHeader title="Growth opportunities"
            action={<Link href={`/companies/${companyId}/opportunities`} className="text-xs font-medium text-navy-600 hover:underline">View all</Link>} />
          <ul className="divide-y divide-slate-100">
            {data.top_opportunities.map((o) => (
              <li key={o.id} className="px-5 py-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-800">{o.title}</span>
                  <span className="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[11px] text-emerald-700">{o.confidence}</span>
                </div>
                <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">{o.description}</p>
              </li>
            ))}
            {data.top_opportunities.length === 0 && (
              <li className="px-5 py-6 text-center text-xs text-slate-400">No opportunities detected yet — run an analysis.</li>
            )}
          </ul>
        </Card>
      </div>

      <Card>
        <CardHeader title="Recent documents"
          action={<Link href={`/companies/${companyId}/documents`} className="text-xs font-medium text-navy-600 hover:underline">Manage documents</Link>} />
        <ul className="divide-y divide-slate-100">
          {data.recent_documents.map((d) => (
            <li key={d.id} className="flex items-center justify-between px-5 py-2.5 text-sm">
              <span className="truncate text-slate-700">{d.filename}</span>
              <span className="flex shrink-0 items-center gap-2 text-xs text-slate-400">
                {DOC_TYPE_LABELS[d.document_type] ?? d.document_type}
                {d.fiscal_year ? ` · FY${d.fiscal_year}` : ""} · {d.status}
              </span>
            </li>
          ))}
          {data.recent_documents.length === 0 && (
            <li className="px-5 py-6 text-center text-xs text-slate-400">No documents uploaded yet.</li>
          )}
        </ul>
      </Card>

      <p className="text-center text-[11px] text-slate-400">
        This tool provides analytical assistance based on available documents and should not be treated as
        financial, legal, tax, or investment advice.
      </p>

      <AnalyzeProgress jobId={jobId} onDone={() => { setJobId(null); toast("success", "Analysis complete."); refresh(); }} />
    </div>
  );
}
