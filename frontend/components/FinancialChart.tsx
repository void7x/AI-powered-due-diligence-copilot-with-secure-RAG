"use client";

import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const COLORS = ["#2f5587", "#0e9f6e", "#d97706", "#b91c1c", "#7c3aed"];

export interface SeriesDef {
  key: string;
  label: string;
  format?: (v: number) => string;
}

export function FinancialChart({ data, series, height = 260 }: {
  data: Record<string, unknown>[];
  series: SeriesDef[];
  height?: number;
}) {
  const fmt = (v: number | string | undefined): string => {
    if (typeof v !== "number") return String(v ?? "");
    const s = series.find((x) => x.format);
    return s?.format ? s.format(v) : v.toLocaleString("en-US", { maximumFractionDigits: 1 });
  };
  return (
    <div style={{ height }} className="w-full" role="img" aria-label={series.map((s) => s.label).join(", ") + " chart"}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="period" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={{ stroke: "#cbd5e1" }} tickLine={false} />
          <YAxis tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} width={56}
                 tickFormatter={(v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 0 })} />
          <Tooltip formatter={(v) => fmt(v as number)} contentStyle={{ fontSize: 12, borderRadius: 6, borderColor: "#e2e8f0" }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s, i) => (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.label}
                  stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={{ r: 3 }}
                  connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
