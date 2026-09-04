"use client";

import { FileText } from "lucide-react";
import { useRouter } from "next/navigation";
import { titleCase } from "@/lib/format";

export function CitationBadge({ companyId, documentId, documentName, page, section, size = "md" }: {
  companyId?: string;
  documentId: string;
  documentName: string;
  page: number;
  section?: string;
  size?: "sm" | "md";
}) {
  const router = useRouter();
  if (!companyId) {
    return (
      <span className="inline-flex items-center gap-1 rounded border border-navy-200 bg-navy-50 px-1.5 py-0.5 text-[11px] font-medium text-navy-700">
        <FileText size={11} />{documentName} · p.{page}
      </span>
    );
  }
  const label = `${documentName} · p.${page}`;
  return (
    <button
      type="button"
      title={`Open ${documentName} at page ${page}${section ? ` — ${titleCase(section)}` : ""}`}
      onClick={() =>
        router.push(`/companies/${companyId}/documents?docId=${documentId}&page=${page}`)
      }
      className={`inline-flex items-center gap-1 rounded border border-navy-200 bg-navy-50 font-medium text-navy-700 transition hover:border-navy-400 hover:bg-navy-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-500/40 ${
        size === "sm" ? "px-1.5 py-0.5 text-[11px]" : "px-2 py-1 text-xs"}`}
    >
      <FileText size={size === "sm" ? 11 : 12} />
      {label}
    </button>
  );
}
