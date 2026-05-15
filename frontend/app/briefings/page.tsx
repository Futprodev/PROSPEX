import Link from "next/link";
import { getCompany, getBriefings, formatDate, scoreColor } from "@/lib/api";

const COMPANY_ID = process.env.NEXT_PUBLIC_COMPANY_ID ?? "";

export default async function BriefingsPage() {
  const [company, briefings] = await Promise.all([
    getCompany(COMPANY_ID),
    getBriefings(COMPANY_ID, 50),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Briefing History</h1>
        {company && (
          <p className="text-sm text-muted-foreground mt-0.5">
            {company.name} · {company.country}
          </p>
        )}
      </div>

      {briefings.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 border rounded-xl gap-3">
          <p className="font-semibold">No briefings yet</p>
          <Link href="/" className="text-sm text-muted-foreground underline">
            Generate one from the dashboard
          </Link>
        </div>
      ) : (
        <div className="border rounded-xl overflow-hidden divide-y shadow-sm">
          {briefings.map((b, i) => (
            <Link
              key={b.id}
              href={`/briefings/${b.id}`}
              className="flex items-center justify-between px-5 py-4 hover:bg-muted/40 transition-colors group"
            >
              <div className="space-y-0.5">
                <p className="text-sm font-medium group-hover:text-foreground">
                  Week of {formatDate(b.week_of ?? b.generated_at)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Generated {formatDate(b.generated_at)}
                </p>
              </div>

              <div className="flex items-center gap-4">
                {i === 0 && (
                  <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded-full font-medium">
                    Latest
                  </span>
                )}
                <span
                  className={`text-xl font-bold tabular-nums ${scoreColor(b.health_score)}`}
                >
                  {b.health_score != null ? Math.round(b.health_score) : "—"}
                </span>
                <span className="text-muted-foreground text-sm">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
