import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { getHeroMetrics, type HeroMetrics } from "@/lib/api";

interface Props {
  companyId: string;
}

function fmtEuro(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  const abs = Math.abs(n);
  // Use locale-independent thousands separator to avoid hydration mismatch
  const grouped = Math.round(abs).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${n < 0 ? "−" : ""}€${grouped}`;
}

function fmtMonths(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  if (n < 1) {
    const days = Math.round(n * 30);
    return `${days}d`;
  }
  return `${n.toFixed(1)} mo`;
}

interface DeltaProps {
  value:          number | null | undefined;
  invertGood?:    boolean;   // true for metrics where lower is better (burn, DSO)
  suffix?:        string;
}

function Delta({ value, invertGood = false, suffix = "" }: DeltaProps) {
  if (value === null || value === undefined) {
    return (
      <span className="text-xs text-muted-foreground inline-flex items-center gap-0.5">
        <Minus className="h-2.5 w-2.5" />
        no prior
      </span>
    );
  }
  if (value === 0) {
    return (
      <span className="text-xs text-muted-foreground inline-flex items-center gap-0.5">
        <Minus className="h-2.5 w-2.5" />
        no change
      </span>
    );
  }
  const isUp = value > 0;
  const isGood = invertGood ? !isUp : isUp;
  const tone = isGood ? "text-emerald-600" : "text-red-500";
  const Icon = isUp ? ArrowUp : ArrowDown;
  const display = Math.abs(value).toLocaleString("en-US", { maximumFractionDigits: 1 });
  return (
    <span className={`text-xs inline-flex items-center gap-0.5 ${tone}`}>
      <Icon className="h-2.5 w-2.5" />
      {display}{suffix}
    </span>
  );
}

interface TileProps {
  label:   string;
  value:   string;
  tone?:   "default" | "danger" | "warning" | "good";
  delta?:  React.ReactNode;
  hint?:   string;
}

function Tile({ label, value, tone = "default", delta, hint }: TileProps) {
  const valueColor = {
    default: "text-foreground",
    danger:  "text-red-600 dark:text-red-400",
    warning: "text-amber-600 dark:text-amber-400",
    good:    "text-emerald-600 dark:text-emerald-400",
  }[tone];
  return (
    <div className="border rounded-xl px-4 py-3 shadow-sm bg-background flex flex-col gap-1 min-w-0">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground truncate">
        {label}
      </span>
      <span className={`text-2xl font-semibold tabular-nums tracking-tight ${valueColor}`}>
        {value}
      </span>
      <div className="flex items-center justify-between gap-2 min-h-[16px]">
        {delta}
        {hint && <span className="text-[10px] text-muted-foreground truncate">{hint}</span>}
      </div>
    </div>
  );
}

function runwayTone(months: number | null): TileProps["tone"] {
  if (months === null) return "default";
  if (months < 3)  return "danger";
  if (months < 6)  return "warning";
  return "good";
}

function profitTone(profit: number | null): TileProps["tone"] {
  if (profit === null) return "default";
  if (profit < 0) return "danger";
  if (profit === 0) return "default";
  return "good";
}

export async function HeroMetricsStrip({ companyId }: Props) {
  const m: HeroMetrics | null = await getHeroMetrics(companyId);
  if (!m) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
      <Tile
        label="Cash"
        value={fmtEuro(m.cash)}
        delta={<Delta value={m.cash_delta} />}
        hint="vs last sync"
      />
      <Tile
        label="Runway"
        value={fmtMonths(m.runway_months)}
        tone={runwayTone(m.runway_months)}
        delta={null}
        hint="at current burn"
      />
      <Tile
        label="Monthly burn"
        value={fmtEuro(m.burn)}
        delta={<Delta value={m.burn_delta_pct} invertGood suffix="%" />}
        hint="vs last sync"
      />
      <Tile
        label="Income this month"
        value={fmtEuro(m.income_this_month)}
        delta={<Delta value={m.income_change_pct} suffix="%" />}
        hint="vs last month"
      />
      <Tile
        label="Net profit this month"
        value={fmtEuro(m.net_profit_this_month)}
        tone={profitTone(m.net_profit_this_month)}
        delta={<Delta value={m.net_profit_change_pct} suffix="%" />}
        hint="vs last month"
      />
    </div>
  );
}
