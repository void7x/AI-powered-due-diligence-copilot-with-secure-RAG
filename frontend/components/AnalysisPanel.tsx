"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Circle, Clock3, Loader2 } from "lucide-react";
import { Modal } from "@/components/ui";
import { apiGet } from "@/lib/api";
import type { Job } from "@/types";

const STEPS = [
  "Preparing evidence",
  "Analyzing financials",
  "Detecting risks",
  "Finding opportunities",
  "Checking inconsistencies",
  "Generating summary",
];

/** Non-blocking analysis progress dialog (polls /api/jobs/{id}). */
export function AnalyzeProgress({ jobId, onDone }: { jobId: string | null; onDone: () => void }) {
  const [job, setJob] = useState<Job | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let stop = false;
    setStartedAt(Date.now());
    const tick = async () => {
      try {
        const j = await apiGet<Job>(`/api/jobs/${jobId}`);
        if (!stop) setJob(j);
        if (j.status === "running") setTimeout(tick, 1200);
        else if (j.status === "succeeded") setTimeout(onDone, 600);
      } catch { if (!stop) setTimeout(tick, 2000); }
    };
    tick();
    return () => { stop = true; };
  }, [jobId, onDone]);

  if (!jobId) return null;
  const stepIndex = job ? STEPS.indexOf(job.current_step) : -1;
  const completedSteps = job?.status === "succeeded" ? STEPS.length : Math.max(stepIndex, 0);
  const etaLabel = job?.status === "succeeded"
    ? "Complete"
    : startedAt && Date.now() - startedAt > 45_000
      ? "Taking a little longer"
      : "Usually under a minute";

  return (
    <Modal open onClose={() => {}} title="Analyzing company">
      <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50/80 p-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-800">Diligence analysis pipeline</p>
            <p className="mt-0.5 text-xs text-slate-500">Building an evidence-backed decision package.</p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-1 text-[11px] font-medium text-slate-500">
            <Clock3 size={12} /> {etaLabel}
          </span>
        </div>
      </div>

      <ol className="space-y-3">
        {STEPS.map((step, i) => {
          const done = Boolean(job && (job.status === "succeeded" || (stepIndex >= 0 && i < stepIndex)));
          const active = job?.status === "running" && job.current_step === step;
          return (
            <li key={step} className="flex items-center gap-3 text-sm">
              {done ? <CheckCircle2 size={17} className="text-emerald-500" />
                : active ? <Loader2 size={17} className="animate-spin text-navy-600" />
                : <Circle size={17} className="text-slate-300" />}
              <span className={done || active ? "text-slate-800" : "text-slate-400"}>{step}</span>
              {active && <span className="ml-auto text-[11px] text-slate-400">Working</span>}
            </li>
          );
        })}
      </ol>

      <div className="mt-4 flex items-center justify-between text-[11px] text-slate-400">
        <span>{completedSteps}/{STEPS.length} stages</span>
        <span>{Math.round(job?.progress ?? 4)}%</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-navy-600 transition-all" style={{ width: `${job?.progress ?? 4}%` }} />
      </div>

      {job?.status === "failed" && (
        <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          Analysis failed: {job.error}
        </p>
      )}
    </Modal>
  );
}
