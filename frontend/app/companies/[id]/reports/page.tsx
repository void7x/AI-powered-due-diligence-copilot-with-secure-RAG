"use client";

import { useState } from "react";
import Link from "next/link";
import { FileText, Play } from "lucide-react";
import { Button, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { AnalyzeProgress } from "@/components/AnalysisPanel";
import { useApiData } from "@/hooks/useApi";
import { useToast } from "@/hooks/useToast";
import { apiPost } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import type { ReportSummary } from "@/types";

export default function ReportsPage({ params }: { params: { id: string } }) {
  const companyId = params.id;
  const { data, error, loading, refresh } = useApiData<ReportSummary[]>(`/api/companies/${companyId}/reports`);
  const [jobId, setJobId] = useState<string | null>(null);
  const { toast } = useToast();

  const generate = async () => {
    try {
      await apiPost(`/api/companies/${companyId}/report`);
      toast("success", "Executive due-diligence report generated.");
      refresh();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Report generation failed");
    }
  };

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={refresh} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">One-click executive summaries with citations, charts-ready financial tables and management questions.</p>
        <Button onClick={generate}><Play size={13} /> Generate report</Button>
      </div>
      {!data || data.length === 0 ? (
        <EmptyState title="No reports yet" icon={<FileText size={24} />}
          hint="Generate an executive due-diligence summary once at least one document is processed." />
      ) : (
        <Card>
          <ul className="divide-y divide-slate-100">
            {data.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <FileText size={16} className="shrink-0 text-navy-600" />
                  <div className="min-w-0">
                    <Link href={`/reports/${r.id}`} className="block truncate text-sm font-medium text-navy-700 hover:underline">
                      {r.title}
                    </Link>
                    <p className="text-xs text-slate-400">
                      {fmtDateTime(r.created_at)} · risk {r.overall_risk_score.toFixed(0)}/100
                      {r.period_from ? ` · ${r.period_from}–${r.period_to}` : ""}
                    </p>
                  </div>
                </div>
                <Link href={`/reports/${r.id}`}><Button size="sm" variant="secondary">View</Button></Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <AnalyzeProgress jobId={jobId} onDone={() => { setJobId(null); refresh(); }} />
    </div>
  );
}
