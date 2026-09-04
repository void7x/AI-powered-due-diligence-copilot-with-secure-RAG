"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";
import { Button, Card, ErrorState, Input, LoadingState, Table } from "@/components/ui";
import { CreateCompanyModal } from "@/components/CreateCompanyModal";
import { useApiData } from "@/hooks/useApi";
import { useToast } from "@/hooks/useToast";
import { apiDelete } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { SeverityBadge } from "@/components/SeverityBadge";
import type { CompanySummary } from "@/types";

export default function CompaniesPage() {
  const { data, error, loading, refresh } = useApiData<CompanySummary[]>("/api/companies");
  const [creating, setCreating] = useState(false);
  const { toast } = useToast();

  const remove = async (company: CompanySummary) => {
    if (!window.confirm(`Delete "${company.name}" and all its documents/analyses? This cannot be undone.`)) return;
    try {
      await apiDelete(`/api/companies/${company.id}`);
      toast("success", "Company deleted.");
      refresh();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Companies</h1>
          <p className="text-sm text-slate-500">Each company is an isolated research workspace</p>
        </div>
        <Button onClick={() => setCreating(true)}><Plus size={14} /> New company</Button>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} retry={refresh} />}
      {data && (data.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-12 text-center">
          <p className="text-sm font-medium text-slate-700">No companies yet</p>
          <p className="mt-1 text-xs text-slate-500">Create one to start uploading filings and running AI due diligence.</p>
          <Button className="mt-4" onClick={() => setCreating(true)}><Plus size={14} /> New company</Button>
        </div>
      ) : (
        <Card>
          <Table head={["Company", "Ticker", "Industry", "Docs", "Risk", "Health", "Growth", "Last analyzed", ""]}>
            {data.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50/60">
                <td className="td">
                  <Link href={`/companies/${c.id}`} className="font-medium text-navy-700 hover:text-navy-900 hover:underline">
                    {c.name}
                  </Link>
                </td>
                <td className="td">{c.ticker || "—"}</td>
                <td className="td max-w-[200px] truncate">{c.industry || "—"}</td>
                <td className="td tabular-nums">{c.document_count}</td>
                <td className="td"><SeverityBadge level={c.risk_level} /></td>
                <td className="td tabular-nums">{c.financial_health ?? "—"}</td>
                <td className="td tabular-nums">{c.growth_potential ?? "—"}</td>
                <td className="td text-slate-500">{c.last_analyzed_at ? fmtDate(c.last_analyzed_at) : "—"}</td>
                <td className="td text-right">
                  <Button variant="danger" size="sm" onClick={() => remove(c)}>Delete</Button>
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      ))}

      <CreateCompanyModal open={creating} onClose={() => setCreating(false)} onCreated={refresh} />
    </main>
  );
}
