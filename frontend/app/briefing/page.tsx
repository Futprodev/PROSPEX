import Link from "next/link";
import {
  getCompany,
  getLatestBriefing,
  getBriefings,
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
import { BenchmarkCard } from "@/components/benchmark-card";
import { ConnectXeroScreen } from "@/components/connect-xero-screen";

/**
 * The advisory hub. Everything that helps the founder interpret the numbers:
 * the weekly briefing, the health score with trend, the five dimensions,
 * the industry benchmarks, and the history of past briefings.
 */
export default async function BriefingPage() {
  const companyId = await getActiveCompanyId();
  const company   = companyId ? await getCompany(companyId) : null;

  if (!company) {
    return <ConnectXeroScreen />;
  }

  const [briefing, history] = await Promise.all([
    getLatestBriefing(companyId),
    getBriefings(companyId, 8),
  ]);

  const parsed        = briefing ? parseBriefingText(briefing.full_briefing) : null;
  const dimensions    = briefing ? parseDimensions(briefing.financial_summary) : [];
  const previousScore = history.length > 1 ? history[1].health_score : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Briefing</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          AI-generated advisory for {company.name} · updated every Monday at 07:00
        </p>
      </div>

      {briefing && parsed ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">

          {/* Left column — briefing on top, benchmarks + past briefings below */}
          <div className="lg:col-span-2 space-y-6">
            <BriefingSections
              parsed={parsed}
              weekOf={`Week of ${formatDate(briefing.week_of ?? briefing.generated_at)}`}
            />

            {/* 50:50 row under the briefing — benchmarks + past briefings */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

          {/* Right column — score, trend, dimensions */}
          <div className="space-y-4">
            <HealthScoreCard
              score={briefing.health_score}
              previousScore={previousScore}
            />
            <ScoreTrendChart history={history} />
            <DimensionBreakdown dimensions={dimensions} />
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-24 border rounded-xl gap-3">
          <p className="font-semibold">No briefing yet</p>
          <p className="text-sm text-muted-foreground">
            Open the company menu in the header and choose{" "}
            <span className="font-medium text-foreground">Generate briefing</span>.
          </p>
        </div>
      )}
    </div>
  );
}
