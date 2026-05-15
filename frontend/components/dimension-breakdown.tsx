import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ParsedDimension } from "@/lib/api";

interface Props {
  dimensions: ParsedDimension[];
}

function barColor(score: number): string {
  if (score >= 65) return "bg-emerald-500";
  if (score >= 40) return "bg-amber-400";
  if (score >= 25) return "bg-orange-500";
  return "bg-red-500";
}

function labelStyle(label: string): string {
  switch (label.toLowerCase()) {
    case "good":     return "text-emerald-700 bg-emerald-50 border-emerald-200 dark:text-emerald-400 dark:bg-emerald-950/40 dark:border-emerald-800";
    case "fair":     return "text-amber-700 bg-amber-50 border-amber-200 dark:text-amber-400 dark:bg-amber-950/40 dark:border-amber-800";
    case "poor":     return "text-orange-700 bg-orange-50 border-orange-200 dark:text-orange-400 dark:bg-orange-950/40 dark:border-orange-800";
    case "critical": return "text-red-700 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-950/40 dark:border-red-800";
    default:         return "text-muted-foreground bg-muted border-border";
  }
}

export function DimensionBreakdown({ dimensions }: Props) {
  if (!dimensions.length) return null;

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Financial Dimensions
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {dimensions.map((d) => (
          <div key={d.name}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-medium">{d.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-sm tabular-nums text-muted-foreground">
                  {Math.round(d.score)}
                </span>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded border font-medium capitalize ${labelStyle(d.label)}`}
                >
                  {d.label}
                </span>
              </div>
            </div>
            <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${barColor(d.score)}`}
                style={{ width: `${Math.min(d.score, 100)}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
              {d.insight}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
