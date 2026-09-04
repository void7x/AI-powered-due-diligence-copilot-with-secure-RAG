"use client";

import { useEffect, useMemo, useState } from "react";
import { Eye, Filter, RotateCw, Search, Trash2 } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Select, Table } from "@/components/ui";
import { DocumentViewer } from "@/components/DocumentViewer";
import { useApiData, usePoll } from "@/hooks/useApi";
import { apiDelete, apiPost } from "@/lib/api";
import { DOC_TYPE_LABELS, fmtDateTime } from "@/lib/format";
import type { DocumentItem } from "@/types";

const STATUS_TONES: Record<string, string> = {
  READY: "green", FAILED: "red", UPLOADED: "slate",
  PROCESSING: "amber", EXTRACTING: "amber", CHUNKING: "amber", EMBEDDING: "amber", ANALYZING: "amber",
};

export default function DocumentsPage({ params, searchParams }: {
  params: { id: string };
  searchParams: { docId?: string; page?: string; quote?: string };
}) {
  const { id: companyId } = params;
  const sp = searchParams;
  const [query, setQuery] = useState("");
  const [docType, setDocType] = useState("");
  const [year, setYear] = useState("");
  const [sort, setSort] = useState("created_desc");
  const [viewer, setViewer] = useState<{ doc: DocumentItem; page: number; quote?: string } | null>(null);

  const qs = useMemo(() => {
    const p = new URLSearchParams();
    if (query) p.set("q", query);
    if (docType) p.set("document_type", docType);
    if (year) p.set("fiscal_year", year);
    if (sort) p.set("sort", sort);
    return p.toString();
  }, [query, docType, year, sort]);

  const { data, error, loading, refresh } = useApiData<DocumentItem[]>(
    `/api/companies/${companyId}/documents?${qs}`, [qs]);
  const processing = (data ?? []).some((d) => !["READY", "FAILED", "UPLOADED"].includes(d.status));
  const { data: polled } = usePoll<DocumentItem[]>(`/api/companies/${companyId}/documents`, 3000, processing);

  // Citation deep-link: /documents?docId=..&page=..
  const docList = polled ?? data ?? [];
  useEffect(() => {
    if (sp.docId && docList.length && !viewer) {
      const doc = docList.find((d) => d.id === sp.docId);
      if (doc) setViewer({ doc, page: Number(sp.page ?? 1), quote: sp.quote });
    }
  }, [sp.docId, sp.page, sp.quote, docList, viewer]);

  const remove = async (doc: DocumentItem) => {
    if (!window.confirm(`Delete "${doc.filename}"?`)) return;
    try {
      await apiDelete(`/api/documents/${doc.id}`);
      refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const reprocess = async (doc: DocumentItem) => {
    try {
      await apiPost(`/api/documents/${doc.id}/process`);
      refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Reprocess failed");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input className="pl-8" placeholder="Search filenames…" value={query}
                 onChange={(e) => setQuery(e.target.value)} aria-label="Search documents" />
        </div>
        <Filter size={14} className="text-slate-400" aria-hidden />
        <Select className="w-44" value={docType} onChange={(e) => setDocType(e.target.value)} aria-label="Filter by type">
          <option value="">All types</option>
          {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Select>
        <Select className="w-32" value={year} onChange={(e) => setYear(e.target.value)} aria-label="Filter by fiscal year">
          <option value="">All years</option>
          {[2022, 2023, 2024, 2025, 2026].map((y) => <option key={y} value={y}>FY{y}</option>)}
        </Select>
        <Select className="w-40" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort">
          <option value="created_desc">Newest first</option>
          <option value="created_asc">Oldest first</option>
          <option value="name_asc">Name A–Z</option>
        </Select>
        {processing && <Badge tone="amber">Processing… (auto-refreshing)</Badge>}
      </div>

      {loading && <LoadingState label="Loading documents…" />}
      {error && <ErrorState message={error} retry={refresh} />}
      {data && (data.length === 0 ? (
        <EmptyState title="No documents" icon={<Search size={24} />}
          hint="Upload annual reports, investor decks, earnings releases or financial statements using the Upload button above." />
      ) : (
        <Card>
          <Table head={["File", "Type", "FY", "Pages", "Status", "Uploaded", ""]}>
            {docList.map((d) => (
              <tr key={d.id} className="hover:bg-slate-50/60">
                <td className="td max-w-[280px]">
                  <button className="truncate font-medium text-navy-700 hover:underline"
                          onClick={() => setViewer({ doc: d, page: 1 })}>
                    {d.filename}
                  </button>
                  {d.error_message && <p className="mt-0.5 text-[11px] text-red-600">{d.error_message}</p>}
                </td>
                <td className="td">{DOC_TYPE_LABELS[d.document_type] ?? d.document_type}</td>
                <td className="td tabular-nums">{d.fiscal_year ? `FY${d.fiscal_year}` : "—"}</td>
                <td className="td tabular-nums">{d.page_count || "—"}</td>
                <td className="td"><Badge tone={STATUS_TONES[d.status] ?? "slate"}>{d.status}</Badge></td>
                <td className="td whitespace-nowrap text-slate-500">{fmtDateTime(d.created_at)}</td>
                <td className="td text-right">
                  <div className="flex justify-end gap-1">
                    <Button size="sm" variant="ghost" title="Inspect pages"
                            onClick={() => setViewer({ doc: d, page: 1 })}><Eye size={13} /></Button>
                    <Button size="sm" variant="ghost" title="Reprocess"
                            onClick={() => reprocess(d)}><RotateCw size={13} /></Button>
                    <Button size="sm" variant="ghost" title="Delete"
                            onClick={() => remove(d)}><Trash2 size={13} className="text-red-500" /></Button>
                  </div>
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      ))}

      <DocumentViewer open={!!viewer} onClose={() => setViewer(null)}
                      document={viewer?.doc ?? null} page={viewer?.page ?? 1} quote={viewer?.quote} />
    </div>
  );
}
