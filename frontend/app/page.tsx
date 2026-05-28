import Link from "next/link";
import { ArrowRight } from "lucide-react";
import {
  getCompany,
  getLatestBriefing,
  getBriefings,
  parseBriefingText,
  parseDimensions,
  formatDate,
} from "@/lib/api";
import { getActiveCompanyId } from "@/lib/company";
import { HealthScoreCard } from "@/components/health-score-card";
import { DimensionBreakdown } from "@/components/dimension-breakdown";
import { BriefingSections } from "@/components/briefing-sections";
import { HeroMetricsStrip } from "@/components/hero-metrics-strip";
import { ConnectXeroScreen } from "@/components/connect-xero-screen";

/**
 * The dashboard is the 30-second landing page. It surfaces only the three
 * cards that reflect the app's core value proposition:
 *   - the weekly briefing
 *   - the health score
 *   - the dimension breakdown
 *
 * Everything else (charts, debtors, benchmarks, history) lives on /briefing
 * and /financials.
 */
export default async function DashboardPage() {
  const companyId = await getActiveCompanyId();
  const company   = companyId ? await getCompany(companyId) : null;

  if (!company) {
    return <ConnectXeroScreen />;
  }

  const [briefing, history] = await Promise.all([
    getLatestBriefing(companyId),
    getBriefings(companyId, 2), // just need previous for the delta
  ]);

  const parsed        = briefing ? parseBriefingText(briefing.full_briefing) : null;
  const dimensions    = briefing ? parseDimensions(briefing.financial_summary) : [];
  const previousScore = history.length > 1 ? history[1].health_score : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{company.name}</h1>
          <p className="text-sm text-muted-foreground mt-0.5 capitalize">
            {company.country} · {company.industry}
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
          <Link
            href="/financials"
            className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
          >
            View financials <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>

      {/* Hero metrics — the 5-second glance, also shown on /financials */}
      <HeroMetricsStrip companyId={companyId} />

      {briefing && parsed ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Left — the weekly briefing */}
          <div className="lg:col-span-2">
            <BriefingSections
              parsed={parsed}
              weekOf={`Week of ${formatDate(briefing.week_of ?? briefing.generated_at)}`}
            />
          </div>

          {/* Right — health score + dimensions */}
          <div className="space-y-4">
            <HealthScoreCard
              score={briefing.health_score}
              previousScore={previousScore}
            />
            <DimensionBreakdown dimensions={dimensions} />

            <Link
              href="/briefing"
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-1"
            >
              See full advisory page <ArrowRight className="h-3 w-3" />
            </Link>
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
