"use client";

import Link from "next/link";
import { Activity, Building2, FileText, Plus } from "lucide-react";
import { Button, Card, CardHeader, ErrorState, LoadingState } from "@/components/ui";
import { CompanyCard } from "@/components/CompanyCard";
import { useApiData } from "@/hooks/useApi";
import { fmtDateTime } from "@/lib/format";
import type { DashboardData } from "@/types";

export default function DashboardPage() {
  const { data, error, loading, refresh } = useApiData<DashboardData>("/api/dashboard");

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-navy-600">Investment intelligence workspace</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Due Diligence Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Portfolio overview across your company workspaces</p>
        </div>
        <Link href="/companies">
          <Button><Plus size={14} /> New company</Button>
        </Link>
      </div>

      {loading && <LoadingState label="Loading dashboard…" />}
      {error && <ErrorState message={error} retry={refresh} />}
      {data && (
        <div className="space-y-6">
          <Card className="overflow-hidden border-navy-100 bg-gradient-to-r from-slate-50 to-white">
            <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Portfolio pulse</p>
                <p className="mt-1 text-sm text-slate-700">{data.totals.companies ?? 0} companies · {data.totals.documents ?? 0} evidence documents · {data.totals.reports ?? 0} generated reports</p>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                <Activity size={13} /> Evidence workspace active
              </span>
            </div>
          </Card>

          <div className="grid grid-cols-3 gap-4">
            <StatCard icon={<Building2 size={16} />} label="Companies" value={data.totals.companies ?? 0} />
            <StatCard icon={<FileText size={16} />} label="Documents" value={data.totals.documents ?? 0} />
            <StatCard icon={<ActivityIcon />} label="Reports" value={data.totals.reports ?? 0} />
          </div>

          <section>
            <div className="mb-3 flex items-end justify-between">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Company workspaces</h2>
                <p className="mt-0.5 text-xs text-slate-400">Open a workspace to review risk, financials, opportunities and evidence.</p>
              </div>
              <Link href="/companies" className="text-xs font-medium text-navy-600 hover:underline">View all</Link>
            </div>
            {data.companies.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center">
                <p className="text-sm font-medium text-slate-700">No companies yet</p>
                <p className="mt-1 text-xs text-slate-500">Create a company workspace, upload filings and run your first analysis.</p>
                <Link href="/companies" className="mt-4 inline-block">
                  <Button size="sm">Create your first company</Button>
                </Link>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {data.companies.map((c) => <CompanyCard key={c.id} company={c} />)}
              </div>
            )}
          </section>

          <Card>
            <CardHeader title="Recent activity" subtitle="Latest evidence and report events across the portfolio" />
            <ul className="divide-y divide-slate-100">
              {data.recent_activity.map((a, i) => (
                <li key={i} className="flex items-center justify-between gap-3 px-5 py-2.5 text-sm">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${a.kind === "report" ? "bg-navy-500" : "bg-emerald-500"}`} />
                    <Link href={`/companies/${a.company_id}`} className="min-w-0 truncate text-slate-700 hover:text-navy-700">
                      <b className="font-medium">{a.company_name}</b> — {a.label}
                    </Link>
                  </span>
                  <span className="shrink-0 text-xs text-slate-400">{fmtDateTime(a.at)}</span>
                </li>
              ))}
              {data.recent_activity.length === 0 && (
                <li className="px-5 py-6 text-center text-xs text-slate-400">No activity yet.</li>
              )}
            </ul>
          </Card>
        </div>
      )}
    </main>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-navy-50 text-navy-600">{icon}</div>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
        <p className="text-lg font-semibold tabular-nums text-slate-900">{value}</p>
      </div>
    </Card>
  );
}

function ActivityIcon() {
  return <FileText size={16} className="rotate-90" />;
}
