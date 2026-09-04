"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3, Bot, FileText, Files, LayoutDashboard, LineChart, Lightbulb,
  Search, ShieldAlert, Upload,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui";
import { UploadDialog } from "@/components/UploadDialog";
import { useApiData } from "@/hooks/useApi";
import { useAuth } from "@/hooks/useAuth";
import type { Company } from "@/types";

const NAV = [
  { href: "", label: "Overview", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: Files },
  { href: "/financials", label: "Financials", icon: LineChart },
  { href: "/risks", label: "Risks", icon: ShieldAlert },
  { href: "/opportunities", label: "Opportunities", icon: Lightbulb },
  { href: "/chat", label: "Copilot", icon: Bot },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/search", label: "Search", icon: Search },
];

export default function CompanyLayout({ children, params }: { children: React.ReactNode; params: { id: string } }) {
  const companyId = params.id;
  const pathname = usePathname();
  const { data: company } = useApiData<Company>(`/api/companies/${companyId}`);
  const [uploadOpen, setUploadOpen] = useState(false);
  const { user, loading } = useAuth();
  const [ready, setReady] = useState(false);
  useEffect(() => { if (!loading) setReady(true); }, [loading]);
  const basePath = `/companies/${companyId}`;

  if (!ready) return <div className="min-h-screen" />;
  if (!company) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="text-center">
          <p className="text-sm text-slate-500">Company not found or still loading.</p>
          <Link href="/companies" className="mt-2 inline-block text-sm font-medium text-navy-600 hover:underline">Back to companies</Link>
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen">
      <TopBar userName={user?.name ?? user?.email ?? ""} />
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900">{company.name}</h1>
              {company.ticker && (
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-semibold text-slate-600">{company.ticker}</span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              {company.industry || "—"}{company.country ? ` · ${company.country}` : ""}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={() => setUploadOpen(true)}>
              <Upload size={13} /> Upload
            </Button>
            <Link href={`${basePath}/chat`}>
              <Button variant="secondary" size="sm"><Bot size={13} /> Ask Copilot</Button>
            </Link>
          </div>
        </div>
        <nav className="mx-auto max-w-7xl px-6" aria-label="Company sections">
          <div className="flex gap-1 overflow-x-auto pb-0.5">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active = pathname === basePath + href || (href === "" && pathname === basePath);
              return (
                <Link key={href} href={basePath + href}
                  className={`flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-500/40 ${
                    active ? "border-navy-700 text-navy-800" : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800"}`}
                  aria-current={active ? "page" : undefined}>
                  <Icon size={14} /> {label}
                </Link>
              );
            })}
          </div>
        </nav>
      </header>
      <div className="mx-auto max-w-7xl px-6 py-6">{children}</div>
      <UploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)}
                    companyId={companyId} onUploaded={() => window.location.reload()} />
    </div>
  );
}

function TopBar({ userName }: { userName: string }) {
  const { logout } = useAuth();
  return (
    <div className="flex items-center justify-between bg-navy-900 px-6 py-2.5 text-white">
      <Link href="/dashboard" className="flex items-center gap-2 text-sm font-semibold tracking-tight">
        <BarChart3 size={16} /> AI Due Diligence Copilot
      </Link>
      <div className="flex items-center gap-3 text-xs text-navy-100">
        <Link href="/dashboard" className="hover:text-white">Dashboard</Link>
        <Link href="/companies" className="hover:text-white">Companies</Link>
        <span className="text-navy-300">|</span>
        <span>{userName}</span>
        <button onClick={logout} className="rounded border border-navy-600 px-2 py-0.5 text-[11px] hover:bg-navy-800">Sign out</button>
      </div>
    </div>
  );
}
