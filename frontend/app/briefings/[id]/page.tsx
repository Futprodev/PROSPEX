import { notFound } from "next/navigation";
import Link from "next/link";
import {
  getBriefingById,
  parseBriefingText,
  parseDimensions,
  formatDate,
} from "@/lib/api";
import { HealthScoreCard } from "@/components/health-score-card";
import { DimensionBreakdown } from "@/components/dimension-breakdown";
import { BriefingSections } from "@/components/briefing-sections";

const COMPANY_ID = process.env.NEXT_PUBLIC_COMPANY_ID ?? "";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function BriefingDetailPage({ params }: Props) {
  const { id } = await params;
  const briefing = await getBriefingById(COMPANY_ID, id);

  if (!briefing) notFound();

  const parsed = parseBriefingText(briefing.full_briefing);
  const dimensions = parseDimensions(briefing.financial_summary);

  return (
    <div className="space-y-6">
      {/* Back navigation */}
      <div className="flex items-center gap-4">
        <Link
          href="/briefings"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Briefing History
        </Link>
        <span className="text-muted-foreground">·</span>
        <span className="text-sm text-muted-foreground">
          {formatDate(briefing.week_of ?? briefing.generated_at)}
        </span>
      </div>

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-2">
          <BriefingSections
            parsed={parsed}
            weekOf={`Week of ${formatDate(briefing.week_of ?? briefing.generated_at)}`}
          />
        </div>

        <div className="space-y-4">
          <HealthScoreCard score={briefing.health_score} />
          <DimensionBreakdown dimensions={dimensions} />
        </div>
      </div>
    </div>
  );
}
