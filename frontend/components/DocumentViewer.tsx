"use client";

import { useEffect, useMemo, useState } from "react";
import { ExternalLink, FileText } from "lucide-react";
import { Modal, Badge } from "@/components/ui";
import { apiFile, apiGet } from "@/lib/api";
import { DOC_TYPE_LABELS } from "@/lib/format";
import type { DocumentItem, DocumentPage } from "@/types";

/** Page-level document inspector: extracted text + evidence highlighting +
 *  link to the original PDF page. */
export function DocumentViewer({ open, onClose, document: doc, page, quote }: {
  open: boolean;
  onClose: () => void;
  document: DocumentItem | null;
  page: number;
  quote?: string;
}) {
  const [pages, setPages] = useState<DocumentPage[]>([]);
  const [loading, setLoading] = useState(false);
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [current, setCurrent] = useState(page || 1);

  useEffect(() => { if (open) setCurrent(page || 1); }, [open, page]);

  useEffect(() => {
    if (!open || !doc) return;
    setLoading(true);
    setError(null);
    apiGet<DocumentPage[]>(`/api/documents/${doc.id}/pages`)
      .then(setPages)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load document pages"))
      .finally(() => setLoading(false));
  }, [open, doc]);

  const openOriginal = async () => {
    if (!doc || opening) return;
    setOpening(true);
    try {
      const blob = await apiFile(`/api/documents/${doc.id}/file`);
      const url = URL.createObjectURL(blob);
      const target = window.open(
        `${url}${doc.filename.toLowerCase().endsWith(".pdf") ? `#page=${current}` : ""}`,
        "_blank",
        "noopener,noreferrer",
      );
      if (!target) {
        URL.revokeObjectURL(url);
        throw new Error("The browser blocked the new tab. Allow pop-ups and try again.");
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to open the original file");
    } finally {
      setOpening(false);
    }
  };

  const activePage = pages.find((p) => p.page_number === current) ?? null;
  const highlighted = useMemo(() => buildHighlight(activePage?.text ?? "", quote ?? ""), [activePage, quote]);

  return (
    <Modal open={open} onClose={onClose} title={doc?.filename ?? "Document"} wide>
      {doc && (
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <Badge tone="navy">{DOC_TYPE_LABELS[doc.document_type] ?? doc.document_type}</Badge>
          {doc.fiscal_year && <Badge tone="slate">FY{doc.fiscal_year}</Badge>}
          <span>{pages.length || doc.page_count} pages · {doc.status}</span>
          <button
            type="button"
            className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-navy-600 hover:text-navy-800 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={openOriginal}
            disabled={opening}
          >
            <ExternalLink size={12} />
            {opening ? "Opening…" : `Open original ${doc.filename.toLowerCase().endsWith(".pdf") ? `PDF (page ${current})` : "file"}`}
          </button>
        </div>
      )}
      <div className="mb-3 flex items-center gap-2">
        <label htmlFor="page-select" className="text-xs font-medium text-slate-500">Page</label>
        <select
          id="page-select"
          className="input w-24 py-1 text-xs"
          value={current}
          onChange={(e) => setCurrent(Number(e.target.value))}
        >
          {(pages.length ? pages : Array.from({ length: doc?.page_count ?? 1 }, (_, i) => ({ page_number: i + 1 })))
            .map((p) => (
              <option key={p.page_number} value={p.page_number}>p. {p.page_number}</option>
            ))}
        </select>
        {quote && <Badge tone="amber">Highlighting cited evidence</Badge>}
      </div>
      {loading && <p className="py-8 text-center text-sm text-slate-500">Loading page…</p>}
      {error && <p className="py-8 text-center text-sm text-red-600">{error}</p>}
      {!loading && !error && (
        <div className="max-h-[52vh] overflow-y-auto rounded-md border border-slate-200 bg-slate-50/70 p-4">
          <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-slate-800">
            {highlighted.map((part, i) =>
              part.highlight ? (
                <mark key={i} className="rounded bg-amber-200/70 px-0.5">{part.text}</mark>
              ) : (
                <span key={i}>{part.text}</span>
              )
            )}
          </pre>
          {!activePage && <p className="pt-6 text-center text-xs text-slate-400">No extracted text for this page.</p>}
        </div>
      )}
      <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-400">
        <FileText size={11} /> Text is extracted per page and preserved for citation provenance.
      </p>
    </Modal>
  );
}

interface Part { text: string; highlight: boolean }

function buildHighlight(text: string, quote: string): Part[] {
  if (!text) return [];
  if (!quote || quote.length < 8) return [{ text, highlight: false }];
  const norm = (s: string) => s.replace(/\s+/g, " ").trim().toLowerCase();
  const target = norm(quote).slice(0, 60);
  const lines = text.split("\n");
  const parts: Part[] = [];
  let matched = false;
  for (const line of lines) {
    if (!matched && norm(line).includes(target.slice(0, 40))) {
      matched = true;
      parts.push({ text: line, highlight: true });
    } else {
      parts.push({ text: line, highlight: false });
    }
  }
  if (!matched) {
    const flat = norm(text);
    const idx = flat.indexOf(target);
    if (idx >= 0) {
      return [{ text, highlight: false }];
    }
  }
  return parts;
}
