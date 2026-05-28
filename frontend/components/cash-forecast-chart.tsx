"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts";
import { ForecastResponse } from "@/lib/api";

interface Props {
  forecast: ForecastResponse | null;
}

const chartConfig = {
  balance: {
    label: "Projected cash",
    color: "hsl(220 80% 55%)",
  },
} satisfies ChartConfig;

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `€${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `€${Math.round(value / 1_000)}K`;
  return `€${Math.round(value)}`;
}

/**
 * Locale-independent thousands separator. We avoid `toLocaleString()` because
 * it uses the runtime's default locale, which differs between the Node SSR
 * environment and the browser — causing hydration mismatches.
 */
function formatThousands(n: number): string {
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

export function CashForecastChart({ forecast }: Props) {
  if (!forecast || forecast.projection.length === 0 || forecast.monthly_burn === 0) {
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Cash flow forecast
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground py-8 text-center">
            Need cash and burn data to forecast — run a Xero sync first.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Cash flow forecast · Next {forecast.months} months
        </CardTitle>
        <div className="text-xs text-muted-foreground pt-1">
          {forecast.exhausted_at ? (
            <span className="text-red-500 font-medium">
              Cash runs out around {forecast.exhausted_at}
            </span>
          ) : (
            <span>
              Cash stays positive throughout the forecast window
            </span>
          )}
          {" · "}
          burn €{formatThousands(forecast.monthly_burn)}/mo
        </div>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-[220px] w-full">
          <AreaChart
            accessibilityLayer
            data={forecast.projection}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="cashGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-balance)" stopOpacity={0.4} />
                <stop offset="100%" stopColor="var(--color-balance)" stopOpacity={0.02} />
              </linearGradient>
            </defs>
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
            <ReferenceLine y={0} stroke="hsl(0 70% 60%)" strokeDasharray="3 3" />
            <ChartTooltip
              cursor={{ stroke: "hsl(var(--muted))" }}
              content={
                <ChartTooltipContent
                  formatter={(value) => formatCurrency(value as number)}
                />
              }
            />
            <Area
              type="monotone"
              dataKey="balance"
              stroke="var(--color-balance)"
              strokeWidth={2}
              fill="url(#cashGradient)"
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
