"use client";

import { Bot, User } from "lucide-react";
import { Badge } from "@/components/ui";
import { CitationBadge } from "@/components/CitationBadge";
import { titleCase } from "@/lib/format";
import type { ChatMessageItem, Citation } from "@/types";

const CLAIM_TONES: Record<string, string> = {
  fact: "navy", analysis: "purple", recommendation: "green",
  uncertainty: "amber", contradiction: "red",
};

export function ChatMessageView({ message, citations, companyId }: {
  message: ChatMessageItem;
  citations?: Citation[];
  companyId: string;
}) {
  const isUser = message.role === "user";
  const claims = message.meta?.claims ?? [];
  const citationsFor = (sources: string[]) =>
    (citations ?? []).filter((c) => sources.includes(c.source_id));

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`} aria-label={isUser ? "Your message" : "Copilot answer"}>
      {!isUser && (
        <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-navy-700 text-white">
          <Bot size={15} />
        </div>
      )}
      <div className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${isUser ? "bg-navy-700 text-white" : "card"}`}>
        {!isUser && message.meta?.confidence && (
          <div className="mb-1.5 flex items-center gap-2">
            <Badge tone={message.meta.confidence === "high" ? "green" : message.meta.confidence === "medium" ? "amber" : "slate"}>
              Confidence: {message.meta.confidence}
            </Badge>
            {message.meta.insufficient_evidence && <Badge tone="amber">Insufficient evidence</Badge>}
          </div>
        )}
        <p className={`whitespace-pre-wrap leading-relaxed ${isUser ? "text-white" : "text-slate-800"}`}>
          {message.content}
        </p>
        {!isUser && claims.length > 0 && (
          <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
            {claims.map((claim, i) => (
              <div key={i} className="flex flex-wrap items-start gap-x-2 gap-y-1 text-xs">
                <Badge tone={CLAIM_TONES[claim.type] ?? "slate"}>{titleCase(claim.type)}</Badge>
                <span className="min-w-[12rem] flex-1 leading-relaxed text-slate-700">{claim.text}</span>
                <span className="flex flex-wrap gap-1">
                  {citationsFor(claim.sources).map((c) => (
                    <CitationBadge key={c.source_id} companyId={companyId} documentId={c.document_id}
                      documentName={c.document_name} page={c.page_number} size="sm" />
                  ))}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-slate-200 text-slate-600">
          <User size={15} />
        </div>
      )}
    </div>
  );
}
