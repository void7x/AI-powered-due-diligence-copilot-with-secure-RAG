"use client";

import { useState } from "react";
import { Button, Field, Input, Modal, Textarea } from "@/components/ui";
import { useToast } from "@/hooks/useToast";
import { apiPost } from "@/lib/api";

export function CreateCompanyModal({ open, onClose, onCreated }: {
  open: boolean; onClose: () => void; onCreated: (id?: string) => void;
}) {
  const [name, setName] = useState("");
  const [ticker, setTicker] = useState("");
  const [industry, setIndustry] = useState("");
  const [country, setCountry] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await apiPost<{ id: string }>("/api/companies",
        { name, ticker, industry, country, description });
      toast("success", `${name} created.`);
      setName(""); setTicker(""); setIndustry(""); setCountry(""); setDescription("");
      onClose();
      onCreated(created?.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create company");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Create company workspace">
      <form onSubmit={submit} className="space-y-3.5">
        <Field label="Company name *">
          <Input required maxLength={255} value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Industries plc" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Ticker"><Input maxLength={32} value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="ACM" /></Field>
          <Field label="Country"><Input maxLength={120} value={country} onChange={(e) => setCountry(e.target.value)} placeholder="United States" /></Field>
        </div>
        <Field label="Industry"><Input maxLength={120} value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="Industrial manufacturing" /></Field>
        <Field label="Description">
          <Textarea rows={3} maxLength={4000} value={description} onChange={(e) => setDescription(e.target.value)}
                    placeholder="What does the company do? (optional)" />
        </Field>
        {error && <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={busy || !name.trim()}>{busy ? "Creating…" : "Create company"}</Button>
        </div>
      </form>
    </Modal>
  );
}
