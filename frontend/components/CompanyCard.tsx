"use client";

import Link from "next/link";
import { ArrowRight, FileStack, Activity } from "lucide-react";
import { Badge } from "@/components/ui";
import { SeverityBadge } from "@/components/SeverityBadge";
import { fmtDate } from "@/lib/format";
import type { DashboardData } from "@/types";

export function CompanyCard({ company }: { company: DashboardData["companies"][number] }) {
  const risk = company.risk_level || "unknown";
  const readiness = company.document_count > 0 && company.last_analyzed_at ? 100 : company.document_count > 0 ? 60 : 20;
  const readinessLabel = readiness >= 100 ? "Decision-ready" : readiness >= 60 ? "Analysis in progress" : "Needs preparation";
  const readinessTone = readiness >= 100 ? "bg-emerald-100 text-emerald-700" : readiness >= 60 ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600";
  return (
    <Link href={`/companies/${company.id}`} className="card block p-5 transition hover:border-navy-300 hover:shadow-pop focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-500/40">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-slate-900">{company.name}</h3>
          <p className="mt-0.5 text-xs text-slate-500">
            {company.ticker ? `${company.ticker} · ` : ""}{company.industry || "—"}
          </p>
        </div>
        <SeverityBadge level={risk} />
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        <MiniStat label="Docs" value={String(company.document_count)} />
        <MiniStat label="Fin. health" value={company.financial_health != null ? `${company.financial_health}` : "—"} />
        <MiniStat label="Growth" value={company.growth_potential != null ? `${company.growth_potential}` : "—"} />
      </div>
      <div className="mt-3 rounded-md border border-slate-100 bg-slate-50/70 p-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Diligence readiness</p>
            <p className="mt-0.5 text-xs font-semibold text-slate-700">{readinessLabel}</p>
          </div>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${readinessTone}`}>{readiness}%</span>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200">
          <div className="h-full rounded-full bg-navy-600 transition-all" style={{ width: `${readiness}%` }} />
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2.5 text-[11px] text-slate-400">
        <span className="inline-flex items-center gap-1"><FileStack size={11} /> {company.document_count} documents</span>
        <span className="inline-flex items-center gap-1">
          <Activity size={11} /> {company.last_analyzed_at ? `Analyzed ${fmtDate(company.last_analyzed_at)}` : "Not analyzed"}
        </span>
      </div>
      <div className="mt-2 flex items-center justify-end gap-1 text-[11px] font-medium text-navy-600">
        Open workspace <ArrowRight size={11} />
      </div>
    </Link>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-slate-50 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-0.5 text-sm font-semibold tabular-nums text-slate-800">{value}</p>
    </div>
  );
}

export { Badge };
