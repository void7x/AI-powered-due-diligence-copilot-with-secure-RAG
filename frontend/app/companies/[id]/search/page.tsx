"use client";

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Search, ShieldCheck } from "lucide-react";
import { Badge, Button, Card, EmptyState, Input, LoadingState, Select } from "@/components/ui";
import { DocumentViewer } from "@/components/DocumentViewer";
import { apiGet } from "@/lib/api";
import { DOC_TYPE_LABELS } from "@/lib/format";
import type { DocumentItem, SearchHit, SearchOut } from "@/types";

export default function SearchPage({ params }: { params: { id: string } }) {
  const companyId = params.id;
  const [query, setQuery] = useState("");
  const [docType, setDocType] = useState("");
  const [year, setYear] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewer, setViewer] = useState<{ doc: DocumentItem; page: number } | null>(null);
  const [allDocs, setAllDocs] = useState<DocumentItem[]>([]);

  useEffect(() => {
    apiGet<DocumentItem[]>(`/api/companies/${companyId}/documents`).then(setAllDocs).catch(() => {});
  }, [companyId]);

  const run = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (query.trim().length < 2) return;
    setBusy(true);
    setError(null);
    try {
      const p = new URLSearchParams({ q: query });
      if (docType) p.set("document_type", docType);
      if (year) p.set("fiscal_year", year);
      const res = await apiGet<SearchOut>(`/api/companies/${companyId}/search?${p}`);
      setHits(res.hits);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  };

  const openHit = (hit: SearchHit) => {
    const doc = allDocs.find((d) => d.id === hit.document_id);
    if (doc) setViewer({ doc, page: hit.page_number });
  };

  const evidenceStats = useMemo(() => {
    const resultCount = hits?.length ?? 0;
    const uniqueDocs = new Set((hits ?? []).map((h) => h.document_id)).size;
    const sections = new Set((hits ?? []).map((h) => h.section).filter(Boolean)).size;
    return { resultCount, uniqueDocs, sections };
  }, [hits]);

  return (
    <div className="space-y-4">
      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 bg-slate-50/70 px-5 py-4">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-navy-700" />
            <h2 className="text-sm font-semibold text-slate-900">Evidence search</h2>
          </div>
          <p className="mt-1 text-xs text-slate-500">Search the processed evidence base and jump directly to the source page.</p>
        </div>
        <form onSubmit={run} className="flex flex-wrap items-center gap-2 p-4" role="search">
          <div className="relative min-w-[260px] flex-1">
            <Search size={15} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input className="pl-8" placeholder="e.g. customer concentration, debt, revenue…" value={query}
                   onChange={(e) => setQuery(e.target.value)} aria-label="Search query" maxLength={300} />
          </div>
          <Select className="w-44" value={docType} onChange={(e) => setDocType(e.target.value)} aria-label="Document type filter">
            <option value="">All types</option>
            {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
          <Select className="w-32" value={year} onChange={(e) => setYear(e.target.value)} aria-label="Fiscal year filter">
            <option value="">All years</option>
            {[2022, 2023, 2024, 2025, 2026].map((y) => <option key={y} value={y}>FY{y}</option>)}
          </Select>
          <Button type="submit" disabled={busy || query.trim().length < 2}>{busy ? "Searching…" : "Search evidence"}</Button>
        </form>
      </Card>

      {error && <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>}
      {busy && <LoadingState label="Searching evidence…" />}

      {hits && hits.length > 0 && !busy && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <Card className="p-4"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Matches</p><p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">{evidenceStats.resultCount}</p></Card>
            <Card className="p-4"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Source documents</p><p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">{evidenceStats.uniqueDocs}</p></Card>
            <Card className="p-4"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Sections covered</p><p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">{evidenceStats.sections}</p></Card>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between px-1">
              <p className="text-xs font-medium text-slate-500">Evidence matches</p>
              <span className="flex items-center gap-1 text-[11px] text-emerald-600"><CheckCircle2 size={12} /> Source-linked</span>
            </div>
            {hits.map((h, i) => (
              <Card key={i} className="p-4 transition hover:border-navy-300">
                <button className="w-full text-left" onClick={() => openHit(h)}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-navy-700 hover:underline">{h.document_name}</span>
                    <Badge tone="navy">p. {h.page_number}</Badge>
                    {h.section && <Badge tone="slate">{h.section}</Badge>}
                    {h.fiscal_year && <Badge tone="slate">FY{h.fiscal_year}</Badge>}
                    <span className="ml-auto text-[10px] font-medium text-slate-400">relevance {(h.score * 100).toFixed(0)}%</span>
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-600">…{h.excerpt}…</p>
                </button>
              </Card>
            ))}
          </div>
        </>
      )}

      {hits && hits.length === 0 && !busy && (
        <EmptyState title="No evidence found" hint="Try broader keywords, another fiscal year, or remove the document type filter." icon={<Search size={24} />} />
      )}
      {!hits && !busy && !error && (
        <EmptyState title="Search your evidence base"
          hint="Full-text search across every processed page, with document, page, section and relevance context." icon={<Search size={24} />} />
      )}
      <DocumentViewer open={!!viewer} onClose={() => setViewer(null)}
                      document={viewer?.doc ?? null} page={viewer?.page ?? 1} />
    </div>
  );
}
