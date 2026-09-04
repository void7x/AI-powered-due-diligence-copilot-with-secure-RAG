"use client";

import { Badge } from "@/components/ui";
import { CitationBadge } from "@/components/CitationBadge";
import { TrendingUp } from "lucide-react";
import { titleCase } from "@/lib/format";
import type { Opportunity } from "@/types";

export function OpportunityCard({ opportunity, companyId }: { opportunity: Opportunity; companyId: string }) {
  return (
    <div className="card p-5">
      <div className="flex items-start gap-3">
        <TrendingUp size={18} className="mt-0.5 shrink-0 text-emerald-600" />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-900">{opportunity.title}</h3>
            <Badge tone="green">{titleCase(opportunity.category)}</Badge>
            <Badge tone="slate">Confidence: {opportunity.confidence}</Badge>
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-600">{opportunity.description}</p>
          {opportunity.potential_impact && (
            <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
              <span className="font-medium text-slate-600">Potential impact: </span>{opportunity.potential_impact}
            </p>
          )}
          {opportunity.evidence.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {opportunity.evidence.map((e) => (
                <CitationBadge key={e.id} companyId={companyId} documentId={e.document_id}
                  documentName={e.document_name} page={e.page_number} size="sm" />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
