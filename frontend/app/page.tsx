import Link from "next/link";
import {
  getCompany,
  getLatestBriefing,
  getBriefings,
  getMonthlyTrends,
  getForecast,
  parseBriefingText,
  parseDimensions,
  formatDate,
  scoreColor,
} from "@/lib/api";
import { getActiveCompanyId } from "@/lib/company";
import { HealthScoreCard } from "@/components/health-score-card";
import { DimensionBreakdown } from "@/components/dimension-breakdown";
import { BriefingSections } from "@/components/briefing-sections";
import { ScoreTrendChart } from "@/components/score-trend-chart";
import { RevenueExpenseChart } from "@/components/revenue-expense-chart";
import { CashForecastChart } from "@/components/cash-forecast-chart";
import { BenchmarkCard } from "@/components/benchmark-card";
import { AskData } from "@/components/ask-data";
import { ConnectXeroScreen } from "@/components/connect-xero-screen";

export default async function DashboardPage() {
  const companyId = await getActiveCompanyId();
  const company   = companyId ? await getCompany(companyId) : null;

  // No company configured yet → invite the user to connect Xero
  if (!company) {
    return <ConnectXeroScreen />;
  }

  const [briefing, history, trends, forecast] = await Promise.all([
    getLatestBriefing(companyId),
    getBriefings(companyId, 8),
    getMonthlyTrends(companyId),
    getForecast(companyId, 12),
  ]);

  const parsed = briefing ? parseBriefingText(briefing.full_briefing) : null;
  const dimensions = briefing ? parseDimensions(briefing.financial_summary) : [];
  const previousScore = history.length > 1 ? history[1].health_score : null;

  return (
    <div className="space-y-6">
      {/* Page header — just the company name. Actions live in the header menu. */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{company.name}</h1>
        <p className="text-sm text-muted-foreground mt-0.5 capitalize">
          {company.country} · {company.industry}
        </p>
      </div>

      {/* Top row — revenue + cash forecast */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {trends && trends.months.length > 0 && (
          <RevenueExpenseChart trends={trends} />
        )}
        <CashForecastChart forecast={forecast} />
      </div>

      {briefing && parsed ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">

          {/* Left — briefing text + ask-data */}
          <div className="lg:col-span-2 space-y-6">
            <BriefingSections
              parsed={parsed}
              weekOf={`Week of ${formatDate(briefing.week_of ?? briefing.generated_at)}`}
            />
            <AskData companyId={companyId} />
          </div>

          {/* Right — scores + benchmarks + history */}
          <div className="space-y-4">
            <HealthScoreCard
              score={briefing.health_score}
              previousScore={previousScore}
            />
            <ScoreTrendChart history={history} />
            <DimensionBreakdown dimensions={dimensions} />
            <BenchmarkCard companyId={companyId} />

            {history.length > 0 && (
              <div className="border rounded-xl overflow-hidden shadow-sm">
                <div className="flex items-center justify-between px-4 py-3 border-b">
                  <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    Past Briefings
                  </span>
                  <Link
                    href="/briefings"
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    View all
                  </Link>
                </div>
                <div className="divide-y">
                  {history.map((b, i) => (
                    <Link
                      key={b.id}
                      href={`/briefings/${b.id}`}
                      className="flex items-center justify-between px-4 py-2.5 hover:bg-muted/40 transition-colors"
                    >
                      <span className="text-xs text-muted-foreground">
                        {formatDate(b.week_of ?? b.generated_at)}
                      </span>
                      <div className="flex items-center gap-2">
                        {i === 0 && (
                          <span className="text-xs text-muted-foreground">
                            Latest
                          </span>
                        )}
                        <span className={`text-sm font-semibold tabular-nums ${scoreColor(b.health_score)}`}>
                          {b.health_score != null ? Math.round(b.health_score) : "—"}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-24 border rounded-xl gap-3">
          <p className="font-semibold">No briefing yet</p>
          <p className="text-sm text-muted-foreground">
            Open the company menu in the header and choose{" "}
            <span className="font-medium text-foreground">Generate briefing</span>{" "}
            to run the pipeline for the first time.
          </p>
        </div>
      )}
    </div>
  );
}
