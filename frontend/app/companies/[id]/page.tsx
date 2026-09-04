"use client";

import Link from "next/link";
import { useState } from "react";
import { Play } from "lucide-react";
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          {data.ready_document_count}/{data.document_count} documents processed
          {data.last_analyzed_at ? ` · last analyzed ${fmtDate(data.last_analyzed_at)}` : " · not analyzed yet"}
        </p>
        <div className="flex gap-2">
          <Button size="sm" onClick={analyze}><Play size={12} /> Run analysis</Button>
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
