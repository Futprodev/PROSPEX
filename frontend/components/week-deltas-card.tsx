import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { getHeroMetrics } from "@/lib/api";

interface Props {
  companyId: string;
}

interface Row {
  label:       string;
  current:     string;
  delta:       number | null | undefined;
  invertGood?: boolean;
  suffix?:     string;
}

function fmtDelta(delta: number | null | undefined, suffix: string): string {
  if (delta === null || delta === undefined) return "—";
  const sign = delta > 0 ? "+" : delta < 0 ? "−" : "";
  return `${sign}${Math.abs(delta).toLocaleString("en-US", { maximumFractionDigits: 1 })}${suffix}`;
}

function DeltaRow({ row }: { row: Row }) {
  const noChange = row.delta === 0 || row.delta === null || row.delta === undefined;
  const isUp     = (row.delta ?? 0) > 0;
  const isGood   = row.invertGood ? !isUp : isUp;

  let tone  = "text-muted-foreground";
  let Icon  = Minus;
  if (!noChange) {
    tone = isGood ? "text-emerald-600" : "text-red-500";
    Icon = isUp ? ArrowUp : ArrowDown;
  }

  return (
    <div className="flex items-center justify-between px-4 py-2.5">
      <div className="space-y-0.5">
        <p className="text-sm font-medium">{row.label}</p>
        <p className="text-xs text-muted-foreground tabular-nums">{row.current}</p>
      </div>
      <span className={`text-sm font-semibold inline-flex items-center gap-1 ${tone}`}>
        <Icon className="h-3 w-3" />
        {fmtDelta(row.delta, row.suffix ?? "")}
      </span>
    </div>
  );
}

export async function WeekDeltasCard({ companyId }: Props) {
  const m = await getHeroMetrics(companyId);
  if (!m) return null;

  // Hide entirely if there's no prior snapshot to compare against
  const hasAnyDelta =
    m.cash_delta !== null ||
    m.burn_delta_pct !== null ||
    m.dso_delta !== null ||
    m.health_score_delta !== null;
  if (!hasAnyDelta) return null;

  const rows: Row[] = [
    {
      label:   "Cash",
      current: m.cash !== null ? `€${Math.round(m.cash).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}` : "—",
      delta:   m.cash_delta,
      suffix:  "",
    },
    {
      label:      "Days to get paid",
      current:    m.dso_days !== null ? `${Math.round(m.dso_days)} days` : "—",
      delta:      m.dso_delta,
      suffix:     " days",
      invertGood: true, // lower DSO is better
    },
    {
      label:      "Monthly burn",
      current:    m.burn !== null ? `€${Math.round(m.burn).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}` : "—",
      delta:      m.burn_delta_pct,
      suffix:     "%",
      invertGood: true, // lower burn is better
    },
    {
      label:   "Health score",
      current: m.health_score !== null ? `${Math.round(m.health_score)}/100` : "—",
      delta:   m.health_score_delta,
      suffix:  "",
    },
  ];

  return (
    <div className="border rounded-xl overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b">
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          What changed
        </span>
      </div>
      <div className="divide-y">
        {rows.map((r) => (
          <DeltaRow key={r.label} row={r} />
        ))}
      </div>
    </div>
  );
}
