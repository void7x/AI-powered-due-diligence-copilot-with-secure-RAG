"use client";

import { SeverityBadge } from "@/components/SeverityBadge";

function scoreColor(score: number): string {
  if (score >= 65) return "bg-red-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-emerald-500";
}

export function ScoreCard({ label, score, level, detail }: {
  label: string; score: number; level: string; detail?: string;
}) {
  return (
    <div className="card-padded flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
        <SeverityBadge level={level} />
      </div>
      <div className="flex items-end gap-1">
        <span className="text-2xl font-semibold tabular-nums text-slate-900">{score}</span>
        <span className="pb-0.5 text-xs text-slate-400">/100</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100" role="meter" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
        <div className={`h-full rounded-full ${scoreColor(score)}`} style={{ width: `${Math.max(4, Math.min(100, score))}%` }} />
      </div>
      {detail && <p className="text-[11px] leading-snug text-slate-400">{detail}</p>}
    </div>
  );
}
