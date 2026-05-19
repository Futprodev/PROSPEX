"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { MonthlyTrends } from "@/lib/api";

interface Props {
  trends: MonthlyTrends | null;
}

const chartConfig = {
  revenue: {
    label: "Revenue",
    color: "hsl(160 60% 45%)", // emerald
  },
  expenses: {
    label: "Expenses",
    color: "hsl(0 70% 60%)", // red
  },
} satisfies ChartConfig;

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `€${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `€${Math.round(value / 1_000)}K`;
  return `€${Math.round(value)}`;
}

export function RevenueExpenseChart({ trends }: Props) {
  if (!trends || trends.months.length < 2) {
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Revenue vs Expenses
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground py-8 text-center">
            No monthly data available yet. Run a Xero sync to populate.
          </p>
        </CardContent>
      </Card>
    );
  }

  const data = trends.months.map((m, i) => ({
    month: m,
    revenue: trends.revenue[i] ?? 0,
    expenses: trends.expenses[i] ?? 0,
  }));

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Revenue vs Expenses · Last {data.length} months
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-[220px] w-full">
          <BarChart
            accessibilityLayer
            data={data}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          >
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={false}
              tickMargin={6}
              fontSize={10}
              interval={0}
              angle={-30}
              textAnchor="end"
              height={50}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={4}
              fontSize={10}
              tickFormatter={formatCurrency}
            />
            <ChartTooltip
              cursor={{ fill: "hsl(var(--muted))", opacity: 0.3 }}
              content={
                <ChartTooltipContent
                  formatter={(value) => formatCurrency(value as number)}
                />
              }
            />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar
              dataKey="revenue"
              fill="var(--color-revenue)"
              radius={[3, 3, 0, 0]}
            />
            <Bar
              dataKey="expenses"
              fill="var(--color-expenses)"
              radius={[3, 3, 0, 0]}
            />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
