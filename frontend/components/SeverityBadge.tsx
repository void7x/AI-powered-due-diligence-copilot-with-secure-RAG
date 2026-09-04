import { Badge } from "@/components/ui";

const TONES: Record<string, { tone: string; label: string }> = {
  low: { tone: "green", label: "LOW" },
  medium: { tone: "amber", label: "MEDIUM" },
  high: { tone: "red", label: "HIGH" },
  critical: { tone: "red", label: "CRITICAL" },
  elevated: { tone: "amber", label: "ELEVATED" },
  moderate: { tone: "amber", label: "MODERATE" },
  strong: { tone: "green", label: "STRONG" },
  adequate: { tone: "amber", label: "ADEQUATE" },
  weak: { tone: "red", label: "WEAK" },
};

export function SeverityBadge({ level, className }: { level: string; className?: string }) {
  const cfg = TONES[level?.toLowerCase()] ?? { tone: "slate", label: level?.toUpperCase() ?? "?" };
  return <Badge tone={cfg.tone} className={className}>{cfg.label}</Badge>;
}
