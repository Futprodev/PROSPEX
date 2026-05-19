"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import { BriefingListItem, formatDate } from "@/lib/api";

interface Props {
  history: BriefingListItem[];
}

const chartConfig = {
  score: {
    label: "Health Score",
    color: "hsl(220 70% 50%)",
  },
} satisfies ChartConfig;

export function ScoreTrendChart({ history }: Props) {
  // The API returns newest-first; charts read left-to-right, so reverse it.
  // Filter out nulls so the line stays continuous.
  const data = [...history]
    .reverse()
    .filter((b) => b.health_score != null)
    .map((b) => ({
      date: b.week_of ?? b.generated_at.slice(0, 10),
      score: Math.round(b.health_score!),
      label: formatDate(b.week_of ?? b.generated_at).split(" ").slice(0, 2).join(" "),
    }));

  if (data.length < 2) {
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Score Trend
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground py-8 text-center">
            Need at least 2 briefings to show a trend.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Score Trend
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-[180px] w-full">
          <LineChart
            accessibilityLayer
            data={data}
            margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
          >
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              fontSize={10}
            />
            <YAxis
              domain={[0, 100]}
              tickLine={false}
              axisLine={false}
              tickMargin={4}
              fontSize={10}
              ticks={[0, 25, 50, 75, 100]}
            />
            <ChartTooltip
              cursor={{ stroke: "hsl(var(--muted-foreground))", strokeOpacity: 0.3 }}
              content={<ChartTooltipContent indicator="line" />}
            />
            <Line
              dataKey="score"
              type="monotone"
              stroke="var(--color-score)"
              strokeWidth={2}
              dot={{ r: 3, fill: "var(--color-score)" }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
