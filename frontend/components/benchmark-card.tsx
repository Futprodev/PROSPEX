import { getBenchmarks } from "@/lib/api";

interface Props {
  companyId: string;
}

/** Server component: renders the company's metrics next to industry thresholds. */
export async function BenchmarkCard({ companyId }: Props) {
  const data = await getBenchmarks(companyId);
  if (!data || data.items.length === 0) return null;

  return (
    <div className="border rounded-xl overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          vs Industry
        </span>
        <span className="text-xs text-muted-foreground capitalize">
          {data.industry} · {data.country}
        </span>
      </div>
      <div className="divide-y">
        {data.items.map((item) => (
          <BenchmarkRow key={item.key} item={item} />
        ))}
      </div>
    </div>
  );
}

function BenchmarkRow({
  item,
}: {
  item: NonNullable<Awaited<ReturnType<typeof getBenchmarks>>>["items"][number];
}) {
  if (!item.thresholds || item.value == null) {
    return (
      <div className="px-4 py-3">
        <div className="flex items-center justify-between text-sm">
          <span>{item.label}</span>
          <span className="text-muted-foreground">—</span>
        </div>
      </div>
    );
  }

  const { good, average, poor } = item.thresholds;
  // Determine the visual scale's min/max regardless of direction
  const min = Math.min(good, average, poor, item.value);
  const max = Math.max(good, average, poor, item.value);
  const range = max - min || 1;

  const pct = (v: number) => ((v - min) / range) * 100;

  // Label your status
  const status = (() => {
    if (item.higher_is_better) {
      if (item.value >= good) return { label: "Above industry", color: "text-emerald-600" };
      if (item.value >= average) return { label: "Average", color: "text-amber-500" };
      return { label: "Below industry", color: "text-red-500" };
    } else {
      if (item.value <= good) return { label: "Above industry", color: "text-emerald-600" };
      if (item.value <= average) return { label: "Average", color: "text-amber-500" };
      return { label: "Below industry", color: "text-red-500" };
    }
  })();

  const fmt = (n: number) => {
    if (Math.abs(n) >= 100) return n.toFixed(0);
    return n.toFixed(1);
  };

  return (
    <div className="px-4 py-3 space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{item.label}</span>
        <span className={`text-xs font-semibold ${status.color}`}>
          {status.label}
        </span>
      </div>

      {/* Track with benchmark markers */}
      <div className="relative h-2 bg-muted rounded-full">
        {/* Tick markers for poor / avg / good */}
        {[poor, average, good].map((v, i) => (
          <div
            key={i}
            className="absolute top-0 h-2 w-px bg-border"
            style={{ left: `${pct(v)}%` }}
          />
        ))}
        {/* Your value */}
        <div
          className={`absolute -top-0.5 h-3 w-3 rounded-full border-2 border-background ${
            status.color.includes("emerald")
              ? "bg-emerald-500"
              : status.color.includes("amber")
              ? "bg-amber-500"
              : "bg-red-500"
          }`}
          style={{ left: `calc(${pct(item.value)}% - 6px)` }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground tabular-nums">
        <span>
          You: <span className="font-semibold text-foreground">{fmt(item.value)}{item.unit}</span>
        </span>
        <span>
          avg {fmt(average)}{item.unit} · good {fmt(good)}{item.unit}
        </span>
      </div>
    </div>
  );
}
