"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
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

  useEffect(() => {
    if (!jobId) return;
    let stop = false;
    const tick = async () => {
      try {
        const j = await apiGet<Job>(`/api/jobs/${jobId}`);
        if (!stop) setJob(j);
        if (j.status === "running") setTimeout(tick, 1200);
        else if (j.status === "succeeded") setTimeout(onDone, 600);
      } catch { /* retry */ if (!stop) setTimeout(tick, 2000); }
    };
    tick();
    return () => { stop = true; };
  }, [jobId, onDone]);

  if (!jobId) return null;
  const stepIndex = job ? STEPS.indexOf(job.current_step) : -1;
  return (
    <Modal open onClose={() => {}} title="Analyzing company">
      <ol className="space-y-3">
        {STEPS.map((step, i) => {
          const done = job ? job.status === "succeeded" || (stepIndex >= 0 && i < stepIndex) : false;
          const active = job?.status === "running" && job.current_step === step;
          return (
            <li key={step} className="flex items-center gap-3 text-sm">
              {done ? <CheckCircle2 size={17} className="text-emerald-500" />
                : active ? <Loader2 size={17} className="animate-spin text-navy-600" />
                : <Circle size={17} className="text-slate-300" />}
              <span className={done || active ? "text-slate-800" : "text-slate-400"}>{step}</span>
            </li>
          );
        })}
      </ol>
      {job?.status === "failed" && (
        <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          Analysis failed: {job.error}
        </p>
      )}
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-navy-600 transition-all" style={{ width: `${job?.progress ?? 4}%` }} />
      </div>
    </Modal>
  );
}
