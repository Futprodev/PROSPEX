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
import { HealthScoreCard } from "@/components/health-score-card";
import { DimensionBreakdown } from "@/components/dimension-breakdown";
import { BriefingSections } from "@/components/briefing-sections";
import { GenerateButton } from "@/components/generate-button";
const COMPANY_ID = process.env.NEXT_PUBLIC_COMPANY_ID ?? "";

export default async function DashboardPage() {
  const [company, briefing, history] = await Promise.all([
    getCompany(COMPANY_ID),
    getLatestBriefing(COMPANY_ID),
    getBriefings(COMPANY_ID, 8),
  ]);

  if (!company) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center gap-2">
        <p className="text-lg font-semibold">Cannot reach the backend</p>
        <p className="text-sm text-muted-foreground">
          Make sure{" "}
          <code className="bg-muted px-1 py-0.5 rounded text-xs">
            uvicorn main:app --reload --port 8000
          </code>{" "}
          is running in the{" "}
          <code className="bg-muted px-1 py-0.5 rounded text-xs">backend/</code>{" "}
          folder.
        </p>
      </div>
    );
  }

  const parsed = briefing ? parseBriefingText(briefing.full_briefing) : null;
  const dimensions = briefing ? parseDimensions(briefing.financial_summary) : [];
  const previousScore = history.length > 1 ? history[1].health_score : null;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{company.name}</h1>
          <p className="text-sm text-muted-foreground mt-0.5 capitalize">
            {company.country} · {company.industry}
          </p>
        </div>
        <GenerateButton companyId={COMPANY_ID} />
      </div>

      {briefing && parsed ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">

          {/* Left — briefing text */}
          <div className="lg:col-span-2">
            <BriefingSections
              parsed={parsed}
              weekOf={`Week of ${formatDate(briefing.week_of ?? briefing.generated_at)}`}
            />
          </div>

          {/* Right — scores + history */}
          <div className="space-y-4">
            <HealthScoreCard
              score={briefing.health_score}
              previousScore={previousScore}
            />
            <DimensionBreakdown dimensions={dimensions} />

            {/* Recent briefings — lives here, not at the bottom */}
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
            Click{" "}
            <span className="font-medium text-foreground">
              Generate Briefing
            </span>{" "}
            above to run the pipeline for the first time.
          </p>
        </div>
      )}
    </div>
  );
}
