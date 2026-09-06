"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, Play } from "lucide-react";
import { Card, CardHeader, EmptyState, ErrorState, LoadingState, Button } from "@/components/ui";
import { RiskCard } from "@/components/RiskCard";
import { SeverityBadge } from "@/components/SeverityBadge";
import { useApiData } from "@/hooks/useApi";
import { apiPost } from "@/lib/api";
import { useToast } from "@/hooks/useToast";
import { AnalyzeProgress } from "@/components/AnalysisPanel";
import type { Inconsistency, ManagementQuestion, Risk } from "@/types";

type Tab = "risks" | "inconsistencies" | "questions";

export default function RisksPage({ params }: { params: { id: string } }) {
  const companyId = params.id;
  const [tab, setTab] = useState<Tab>("risks");
  const risks = useApiData<Risk[]>(`/api/companies/${companyId}/risks`);
  const inconsistencies = useApiData<Inconsistency[]>(`/api/companies/${companyId}/inconsistencies`);
  const questions = useApiData<ManagementQuestion[]>(`/api/companies/${companyId}/questions`);
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

  const loading = risks.loading || inconsistencies.loading || questions.loading;
  const error = risks.error ?? inconsistencies.error ?? questions.error;
  const riskSummary = useMemo(() => {
    const items = risks.data ?? [];
    const critical = items.filter((r) => ["critical", "CRITICAL"].includes(String(r.severity))).length;
    const high = items.filter((r) => ["high", "HIGH"].includes(String(r.severity))).length;
    const medium = items.filter((r) => ["medium", "MEDIUM"].includes(String(r.severity))).length;
    const top = items[0];
    return { total: items.length, critical, high, medium, top };
  }, [risks.data]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1 rounded-lg border border-slate-200 bg-white p-1" role="tablist">
          {([["risks", `Risks (${risks.data?.length ?? 0})`],
             ["inconsistencies", `Inconsistencies (${inconsistencies.data?.length ?? 0})`],
             ["questions", `Management questions (${questions.data?.length ?? 0})`]] as [Tab, string][]).map(([key, label]) => (
            <button key={key} role="tab" aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                tab === key ? "bg-navy-700 text-white" : "text-slate-600 hover:bg-slate-100"}`}>
              {label}
            </button>
          ))}
        </div>
        <Button size="sm" variant="secondary" onClick={analyze}><Play size={12} /> Re-run analysis</Button>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} retry={risks.refresh} />}

      {!loading && !error && tab === "risks" && (
        (risks.data?.length ?? 0) === 0 ? (
          <EmptyState title="No risks detected yet"
            hint="Run an analysis: the deterministic risk engine evaluates leverage, liquidity, cash conversion, margins, concentration and disclosure signals." />
        ) : (
          <>
            <Card className="overflow-hidden">
              <div className="border-b border-slate-100 bg-slate-50/70 px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={16} className="text-amber-600" />
                    <div>
                      <h2 className="text-sm font-semibold text-slate-900">Risk priority</h2>
                      <p className="text-xs text-slate-500">Focus the next diligence pass on the highest-severity signals.</p>
                    </div>
                  </div>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                    {riskSummary.total} total risks
                  </span>
                </div>
              </div>
              <div className="grid gap-3 p-5 sm:grid-cols-3">
                <div className="rounded-lg border border-red-100 bg-red-50/50 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-red-500">Critical</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">{riskSummary.critical}</p>
                  <p className="mt-1 text-xs text-slate-500">Immediate escalation signals.</p>
                </div>
                <div className="rounded-lg border border-amber-100 bg-amber-50/50 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-600">High</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">{riskSummary.high}</p>
                  <p className="mt-1 text-xs text-slate-500">Priority validation items.</p>
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Next focus</p>
                  {riskSummary.top ? (
                    <a href={`#risk-${riskSummary.top.id}`} className="mt-1 flex items-start gap-2 text-sm font-medium text-navy-700 hover:underline">
                      <span className="line-clamp-2">{riskSummary.top.title}</span>
                      <ArrowRight size={14} className="mt-0.5 shrink-0" />
                    </a>
                  ) : (
                    <p className="mt-1 text-sm text-slate-500">No priority identified.</p>
                  )}
                  <p className="mt-1 text-xs text-slate-500">Start with the first ranked signal.</p>
                </div>
              </div>
            </Card>
            <div className="space-y-3">
              {risks.data!.map((r) => (
                <div key={r.id} id={`risk-${r.id}`}>
                  <RiskCard risk={r} companyId={companyId} />
                </div>
              ))}
            </div>
          </>
        )
      )}

      {!loading && !error && tab === "inconsistencies" && (
        (inconsistencies.data?.length ?? 0) === 0 ? (
          <EmptyState title="No cross-document inconsistencies detected"
            hint="When you upload multiple documents (e.g. an investor deck plus an annual report), claims are cross-checked against reported data." />
        ) : (
          <div className="space-y-3">
            {inconsistencies.data!.map((inc) => (
              <Card key={inc.id} className="p-5">
                <div className="flex items-center gap-2">
                  <SeverityBadge level={inc.severity} />
                  <h3 className="text-sm font-semibold text-slate-900">{inc.topic}</h3>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div className="rounded-md border border-slate-200 bg-slate-50/60 p-3 text-xs leading-relaxed text-slate-700">
                    <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Claim A</p>
                    {inc.claim_a}
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50/60 p-3 text-xs leading-relaxed text-slate-700">
                    <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Claim B</p>
                    {inc.claim_b}
                  </div>
                </div>
                <p className="mt-3 text-xs italic leading-relaxed text-slate-600">{inc.explanation}</p>
              </Card>
            ))}
          </div>
        )
      )}

      {!loading && !error && tab === "questions" && (
        (questions.data?.length ?? 0) === 0 ? (
          <EmptyState title="No questions generated yet"
            hint="Questions are generated from detected risks and opportunities after an analysis run." />
        ) : (
          <Card>
            <CardHeader title="Recommended questions for management" subtitle="Grounded in detected evidence" />
            <ol className="divide-y divide-slate-100">
              {questions.data!.map((q, i) => (
                <li key={q.id} className="px-5 py-3">
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-slate-100 text-[11px] font-semibold text-slate-500">{i + 1}</span>
                    <div>
                      <p className="text-sm text-slate-800">{q.question}</p>
                      <p className="mt-0.5 text-xs text-slate-500">{q.rationale}</p>
                      <span className="mt-1 inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-slate-500">
                        {q.topic.replace(/_/g, " ")} · {q.priority}
                      </span>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </Card>
        )
      )}

      <AnalyzeProgress jobId={jobId} onDone={() => { setJobId(null); toast("success", "Analysis complete."); risks.refresh(); inconsistencies.refresh(); questions.refresh(); }} />
    </div>
  );
}
