"use client";

export function MetricCard({ label, value, sub, trend }: {
  label: string; value: string; sub?: string; trend?: "up" | "down" | "flat";
}) {
  return (
    <div className="card-padded">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1.5 text-xl font-semibold tabular-nums text-slate-900">{value}</p>
      {sub && (
        <p className={`mt-0.5 text-xs ${trend === "up" ? "text-emerald-600" : trend === "down" ? "text-red-600" : "text-slate-500"}`}>
          {sub}
        </p>
      )}
    </div>
  );
}
