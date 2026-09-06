"use client";

import { useState } from "react";
import { Printer } from "lucide-react";
import { Button, Badge, Table } from "@/components/ui";
import { SeverityBadge } from "@/components/SeverityBadge";
import { CitationBadge } from "@/components/CitationBadge";
import { API_URL, getToken } from "@/lib/api";
import { fmtDateTime, fmtMoney, fmtNumber, fmtPct, titleCase } from "@/lib/format";
import type { ReportContent } from "@/types";

export function ReportView({ report, content }: { report: { id: string }; content: ReportContent }) {
  const scores = content.scores;
  const [openingHtml, setOpeningHtml] = useState(false);

  const openStandaloneHtml = async () => {
    if (openingHtml) return;
    setOpeningHtml(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/api/reports/${report.id}/html`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`Could not open report HTML (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const target = window.open(url, "_blank", "noopener,noreferrer");
      if (!target) {
        URL.revokeObjectURL(url);
        throw new Error("The browser blocked the new tab. Allow pop-ups and try again.");
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Could not open report HTML");
    } finally {
      setOpeningHtml(false);
    }
  };

  return (
    <article className="mx-auto max-w-4xl">
      <header className="border-b-2 border-navy-800 pb-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-navy-900">Executive Due Diligence Summary</h1>
            <p className="mt-1 text-sm text-slate-600">
              <span className="font-semibold">{content.company.name}</span>
              {content.company.ticker ? ` (${content.company.ticker})` : ""} · {content.company.industry}
              {content.company.country ? ` · ${content.company.country}` : ""}
            </p>
            <p className="mt-0.5 text-xs text-slate-400">Generated {fmtDateTime(content.generated_at)} UTC</p>
          </div>
          <div className="no-print flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => window.print()}>
              <Printer size={13} /> Print / PDF
            </Button>
            <button
              type="button"
              onClick={openStandaloneHtml}
              disabled={openingHtml}
              className="inline-flex items-center rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {openingHtml ? "Opening…" : "Standalone HTML"}
            </button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <span className="flex items-center gap-1.5">Overall risk: <b>{scores.overall_risk.toFixed(0)}</b>/100</span>
          <span className="flex items-center gap-1.5">Financial health: <b>{scores.financial_health?.[0]}</b>/100
            <SeverityBadge level={scores.financial_health?.[1] ?? ""} /></span>
          <span className="flex items-center gap-1.5">Growth: <b>{scores.growth_potential?.[0]}</b>/100
            <SeverityBadge level={scores.growth_potential?.[1] ?? ""} /></span>
        </div>
      </header>

      <Section title="Documents analyzed">
        <ul className="list-inside list-disc text-xs text-slate-600">
          {content.documents_analyzed.map((d) => (
            <li key={d.id}>{d.filename} ({titleCase(d.type)}{d.fiscal_year ? `, FY${d.fiscal_year}` : ""})</li>
          ))}
        </ul>
      </Section>

      {(Object.keys(NARRATIVE_TITLES) as (keyof typeof NARRATIVE_TITLES)[]).map((key) =>
        content.narrative[key] ? (
          <Section key={key} title={NARRATIVE_TITLES[key]}>
            <p className="text-sm leading-relaxed text-slate-700">{content.narrative[key]}</p>
          </Section>
        ) : null
      )}

      <Section title="Financial summary">
        <Table head={["Period", "Revenue", "Gross m.", "Op. m.", "Net income", "EBITDA", "Debt", "OCF"]}>
          {content.financial_table.map((row) => (
            <tr key={String(row.period)} className="hover:bg-slate-50/60">
              <td className="td font-semibold">{String(row.period)}</td>
              <td className="td text-right tabular-nums">{fmtMoney(row.revenue as number)}</td>
              <td className="td text-right tabular-nums">{fmtPct(row.gross_margin as number)}</td>
              <td className="td text-right tabular-nums">{fmtPct(row.operating_margin as number)}</td>
              <td className="td text-right tabular-nums">{fmtMoney(row.net_income as number)}</td>
              <td className="td text-right tabular-nums">{fmtMoney(row.ebitda as number)}</td>
              <td className="td text-right tabular-nums">{fmtMoney(row.total_debt as number)}</td>
              <td className="td text-right tabular-nums">{fmtMoney(row.operating_cash_flow as number)}</td>
            </tr>
          ))}
        </Table>
      </Section>

      <Section title="Key risks">
        <div className="space-y-3">
          {content.risks.map((r, i) => (
            <div key={i} className="rounded-md border border-slate-200 p-3">
              <div className="flex items-center gap-2">
                <SeverityBadge level={r.severity} />
                <h4 className="text-sm font-semibold text-slate-800">{r.title}</h4>
                <Badge tone="slate">{titleCase(r.category)}</Badge>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-600">{r.explanation}</p>
              {r.why_it_matters && <p className="mt-1 text-xs text-slate-500"><b>Why it matters:</b> {r.why_it_matters}</p>}
              {r.recommendation && <p className="mt-1 text-xs text-slate-500"><b>Investigate:</b> {r.recommendation}</p>}
              {r.evidence?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {r.evidence.map((e, j) => (
                    <CitationBadge key={j} documentId={e.document_id} documentName={e.document_name} page={e.page_number} size="sm" />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </Section>

      <Section title="Growth opportunities">
        <ul className="space-y-2">
          {content.opportunities.map((o, i) => (
            <li key={i} className="rounded-md border border-emerald-100 bg-emerald-50/40 p-3">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-semibold text-slate-800">{o.title}</h4>
                <Badge tone="green">Confidence: {o.confidence}</Badge>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-slate-600">{o.description}</p>
            </li>
          ))}
          {!content.opportunities.length && <p className="text-xs text-slate-500">None detected.</p>}
        </ul>
      </Section>

      <Section title="Cross-document inconsistencies">
        <div className="space-y-2">
          {content.inconsistencies.map((i) => (
            <div key={i.id} className="rounded-md border border-amber-200 bg-amber-50/50 p-3 text-xs">
              <div className="flex items-center gap-2"><SeverityBadge level={i.severity} />
                <b className="text-slate-800">{i.topic}</b></div>
              <p className="mt-1.5"><b>A:</b> {i.claim_a}</p>
              <p className="mt-0.5"><b>B:</b> {i.claim_b}</p>
              <p className="mt-1 italic text-slate-600">{i.explanation}</p>
            </div>
          ))}
          {!content.inconsistencies.length && <p className="text-xs text-slate-500">None detected.</p>}
        </div>
      </Section>

      <Section title="Key questions for management">
        <ol className="list-inside list-decimal space-y-1.5 text-sm text-slate-700">
          {content.questions.map((q, i) => (
            <li key={i}>
              {q.question} <span className="text-[11px] uppercase text-slate-400">[{q.priority}]</span>
            </li>
          ))}
        </ol>
      </Section>

      <footer className="mt-8 rounded-md border-l-4 border-slate-300 bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-500">
        {content.disclaimer}
      </footer>
    </article>
  );
}

const NARRATIVE_TITLES: Record<string, string> = {
  company_overview: "Company overview",
  business_model: "Business model",
  financial_performance: "Financial performance",
  financial_health: "Financial health",
  key_strengths: "Key strengths",
  key_risks: "Key risks",
  growth_opportunities: "Growth opportunities",
  competitive_position: "Competitive position",
  management_commentary: "Management commentary",
  red_flags: "Potential red flags",
  inconsistencies: "Cross-document inconsistencies",
  questions_for_management: "Key questions for management",
  overall_assessment: "Overall assessment",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="mb-2 border-b border-slate-200 pb-1 text-base font-semibold text-navy-800">{title}</h2>
      {children}
    </section>
  );
}
