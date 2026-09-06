"use client";

import { ArrowUpRight, Sparkles } from "lucide-react";
import { EmptyState, ErrorState, LoadingState, Card } from "@/components/ui";
import { OpportunityCard } from "@/components/OpportunityCard";
import { useApiData } from "@/hooks/useApi";
import type { Opportunity } from "@/types";

export default function OpportunitiesPage({ params }: { params: { id: string } }) {
  const companyId = params.id;
  const { data, error, loading, refresh } = useApiData<Opportunity[]>(`/api/companies/${companyId}/opportunities`);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={refresh} />;
  if (!data || data.length === 0) {
    return <EmptyState title="No opportunities detected yet"
      hint="The opportunity engine looks for revenue growth, margin expansion, R&D acceleration, international expansion and balance-sheet strength." />;
  }

  const confidenceScore = Math.round(data.reduce((sum, o) => {
    const value = String(o.confidence).toLowerCase();
    return sum + (value.includes("high") ? 100 : value.includes("medium") ? 65 : 35);
  }, 0) / data.length);
  const strongest = data[0];
  const highConfidence = data.filter((o) => String(o.confidence).toLowerCase().includes("high")).length;

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 bg-slate-50/70 px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-navy-700" />
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Growth opportunity signal</h2>
                <p className="mt-0.5 text-xs text-slate-500">Prioritized upside surfaced from the evidence set.</p>
              </div>
            </div>
            <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700">
              {highConfidence} high-confidence signal{highConfidence === 1 ? "" : "s"}
            </span>
          </div>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-3">
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Opportunity score</p>
            <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900">{confidenceScore}/100</p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${confidenceScore}%` }} />
            </div>
            <p className="mt-1 text-xs text-slate-500">Average confidence across detected opportunities.</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Upside signals</p>
            <p className="mt-2 text-2xl font-bold tabular-nums text-slate-900">{data.length}</p>
            <p className="mt-1 text-xs text-slate-500">Distinct evidence-backed growth themes identified.</p>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Lead opportunity</p>
            <p className="mt-2 line-clamp-2 text-sm font-semibold text-slate-800">{strongest.title}</p>
            <p className="mt-1 flex items-center gap-1 text-xs text-navy-700"><ArrowUpRight size={12} /> Validate this upside first</p>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {data.map((o) => <OpportunityCard key={o.id} opportunity={o} companyId={companyId} />)}
      </div>
    </div>
  );
}
