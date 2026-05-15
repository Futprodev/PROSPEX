import { Card, CardContent } from "@/components/ui/card";
import { scoreColor, scoreBg, scoreBorderColor } from "@/lib/api";

interface Props {
  score: number | null;
  previousScore?: number | null;
}

export function HealthScoreCard({ score, previousScore }: Props) {
  const delta =
    score != null && previousScore != null ? score - previousScore : null;

  return (
    <Card
      className={`shadow-sm border-2 ${scoreBorderColor(score)} ${scoreBg(score)}`}
    >
      <CardContent className="pt-6 pb-5 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">
          Health Score
        </p>
        <p
          className={`text-7xl font-bold tabular-nums leading-none ${scoreColor(score)}`}
        >
          {score != null ? Math.round(score) : "—"}
        </p>
        <p className="text-sm text-muted-foreground mt-1">/100</p>
        {delta != null && (
          <p
            className={`text-sm font-medium mt-4 ${
              delta >= 0 ? "text-emerald-600" : "text-red-500"
            }`}
          >
            {delta >= 0 ? "+" : ""}
            {delta.toFixed(1)} pts vs last week
          </p>
        )}
        {delta == null && (
          <p className="text-xs text-muted-foreground mt-4">First briefing</p>
        )}
      </CardContent>
    </Card>
  );
}
