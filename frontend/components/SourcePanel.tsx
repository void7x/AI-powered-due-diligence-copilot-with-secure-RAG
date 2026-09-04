"use client";

import { CitationBadge } from "@/components/CitationBadge";
import { Badge } from "@/components/ui";
import type { Citation } from "@/types";

export function SourcePanel({ citations, companyId }: { citations: Citation[]; companyId: string }) {
  if (!citations.length) return null;
  return (
    <div className="card">
      <div className="border-b border-slate-100 px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sources used ({citations.length})</h3>
      </div>
      <ul className="divide-y divide-slate-100">
        {citations.map((c) => (
          <li key={c.source_id} className="px-4 py-3">
            <div className="flex items-center gap-2">
              <Badge tone="navy">{c.source_id}</Badge>
              <CitationBadge companyId={companyId} documentId={c.document_id}
                documentName={c.document_name} page={c.page_number} section={c.section} size="sm" />
            </div>
            {c.quote && <p className="mt-1.5 line-clamp-3 text-[11px] italic leading-relaxed text-slate-500">“{c.quote}”</p>}
            {c.relevance > 0 && <p className="mt-1 text-[10px] text-slate-400">Relevance {(c.relevance * 100).toFixed(0)}%</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
