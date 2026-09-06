import { Badge } from "@/components/ui";
import type { ReportContent } from "@/types";

export function ExecutiveDecisionCard({ content }: { content: ReportContent }) {
  const risk = content.scores.overall_risk;
  const growth = content.scores.growth_potential?.[0] ?? null;
  const documents = content.documents_analyzed.length;
  const inconsistencies = content.inconsistencies.length;
  const recommendation =
    risk >= 70 && (growth == null || growth < 60)
      ? "Proceed with caution"
      : risk >= 70
        ? "Investigate before proceeding"
        : growth != null && growth >= 70 && risk < 45
          ? "Strong candidate for deeper diligence"
          : "Continue diligence";

  const tone = recommendation === "Strong candidate for deeper diligence"
    ? "green"
    : recommendation === "Proceed with caution"
      ? "red"
      : recommendation === "Investigate before proceeding"
        ? "yellow"
        : "slate";

  return (
    <section className="mt-5 rounded-lg border border-navy-100 bg-slate-50/80 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Executive decision</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold text-navy-900">{recommendation}</h2>
            <Badge tone={tone}>{documents} documents analyzed</Badge>
          </div>
          <p className="mt-1.5 max-w-2xl text-xs leading-relaxed text-slate-600">
            {content.narrative.overall_assessment || "Use the evidence below to validate the current diligence posture before making a final decision."}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-3">
          <Metric label="Risk" value={`${risk.toFixed(0)}/100`} />
          <Metric label="Growth" value={growth == null ? "—" : `${growth.toFixed(0)}/100`} />
          <Metric label="Inconsistencies" value={String(inconsistencies)} />
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-0.5 font-semibold tabular-nums text-slate-800">{value}</p>
    </div>
  );
}
