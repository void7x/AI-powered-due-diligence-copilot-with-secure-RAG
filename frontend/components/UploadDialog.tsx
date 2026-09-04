"use client";

import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { Button, Input, Modal, Select } from "@/components/ui";
import { uploadFiles } from "@/lib/api";
import { DOC_TYPE_LABELS } from "@/lib/format";
import { useToast } from "@/hooks/useToast";

const DOC_TYPES = Object.keys(DOC_TYPE_LABELS);

export function UploadDialog({ open, onClose, companyId, onUploaded }: {
  open: boolean; onClose: () => void; companyId: string; onUploaded: () => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [docType, setDocType] = useState("");
  const [fiscalYear, setFiscalYear] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const submit = async () => {
    if (!files.length) return;
    setBusy(true);
    try {
      await uploadFiles(companyId, files, {
        document_type: docType || undefined,
        fiscal_year: fiscalYear || undefined,
      });
      toast("success", `${files.length} document(s) uploaded — processing started.`);
      setFiles([]);
      onUploaded();
      onClose();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Upload documents">
      <div className="space-y-4">
        <div
          role="button" tabIndex={0} aria-label="Choose files to upload"
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault(); setDragOver(false);
            setFiles(Array.from(e.dataTransfer.files));
          }}
          className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center transition ${
            dragOver ? "border-navy-400 bg-navy-50" : "border-slate-300 bg-slate-50 hover:border-navy-300"}`}
        >
          <UploadCloud size={26} className="text-slate-400" />
          <p className="text-sm font-medium text-slate-700">Drop files here or click to browse</p>
          <p className="text-xs text-slate-500">PDF, DOCX, PPTX, XLSX, CSV, TXT — up to 50 MB each</p>
          <input ref={inputRef} type="file" multiple accept=".pdf,.docx,.pptx,.xlsx,.csv,.txt"
                 className="hidden" aria-hidden
                 onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
        </div>
        {files.length > 0 && (
          <ul className="space-y-1 rounded-md border border-slate-200 bg-white p-2 text-xs text-slate-600">
            {files.map((f) => (
              <li key={f.name} className="flex justify-between gap-2">
                <span className="truncate">{f.name}</span>
                <span className="shrink-0 text-slate-400">{(f.size / 1024 / 1024).toFixed(2)} MB</span>
              </li>
            ))}
          </ul>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="up-type" className="label">Document type (optional)</label>
            <Select id="up-type" value={docType} onChange={(e) => setDocType(e.target.value)}>
              <option value="">Auto-detect</option>
              {DOC_TYPES.map((t) => <option key={t} value={t}>{DOC_TYPE_LABELS[t]}</option>)}
            </Select>
          </div>
          <div>
            <label htmlFor="up-year" className="label">Fiscal year (optional)</label>
            <Input id="up-year" type="number" min={1990} max={2100} placeholder="Auto-detect"
                   value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} />
          </div>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-400">
          Files are validated (type, size, content), deduplicated by SHA-256 hash, then processed:
          pages extracted, chunked, embedded and analyzed.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button onClick={submit} disabled={!files.length || busy}>
            {busy ? "Uploading…" : `Upload ${files.length || ""} file${files.length === 1 ? "" : "s"}`}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
