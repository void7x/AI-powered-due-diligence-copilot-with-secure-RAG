"use client";

import { useState } from "react";
import { ChevronDown, Search, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui";
import { SeverityBadge } from "@/components/SeverityBadge";
import { CitationBadge } from "@/components/CitationBadge";
import { titleCase } from "@/lib/format";
import type { Risk } from "@/types";

export function RiskCard({ risk, companyId }: { risk: Risk; companyId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <button
        className="flex w-full items-start justify-between gap-3 px-5 py-4 text-left"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <div className="flex items-start gap-3">
          <ShieldAlert
            size={18}
            className={`mt-0.5 shrink-0 ${risk.severity === "high" || risk.severity === "critical" ? "text-red-500" : risk.severity === "medium" ? "text-amber-500" : "text-emerald-500"}`}
          />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-900">{risk.title}</h3>
              <SeverityBadge level={risk.severity} />
              <Badge tone="slate">{titleCase(risk.category)}</Badge>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">{risk.explanation}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-sm font-semibold tabular-nums text-slate-500">{Math.round(risk.score)}</span>
          <ChevronDown size={16} className={`mt-0.5 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`} />
        </div>
      </button>
      {open && (
        <div className="border-t border-slate-100 px-5 py-4">
          <dl className="grid gap-3 text-sm md:grid-cols-2">
            <Detail label="What we found" value={risk.explanation} />
            <Detail label="Why it matters" value={risk.why_it_matters} />
            <Detail label="Potential impact" value={risk.potential_impact} />
            <Detail label="What to investigate next" value={risk.recommendation} />
          </dl>
          {Object.keys(risk.detected_signals ?? {}).length > 0 && (
            <div className="mt-3 rounded border border-slate-200 bg-slate-50/70 p-3">
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Detected signals</p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(risk.detected_signals).map(([k, v]) => (
                  <Badge key={k} tone="navy">{k}: {String(v)}</Badge>
                ))}
              </div>
            </div>
          )}
          <div className="mt-3">
            <p className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              <Search size={11} /> Evidence
            </p>
            {risk.evidence.length === 0 && <p className="text-xs text-slate-500">Derived from computed financial data.</p>}
            <div className="flex flex-col gap-1.5">
              {risk.evidence.map((e) => (
                <div key={e.id} className="flex flex-col gap-1 rounded border border-slate-200 bg-white px-3 py-2">
                  <CitationBadge companyId={companyId} documentId={e.document_id} documentName={e.document_name} page={e.page_number} />
                  {e.quote && <p className="text-xs italic leading-relaxed text-slate-600">“{e.quote}”</p>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-xs leading-relaxed text-slate-700">{value}</dd>
    </div>
  );
}
