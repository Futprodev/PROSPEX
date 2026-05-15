import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ParsedBriefing } from "@/lib/api";

interface SectionProps {
  title: string;
  content: string;
  accent: string; // left-border + label color
}

function Section({ title, content, accent }: SectionProps) {
  if (!content) return null;
  return (
    <div className={`pl-4 border-l-2 ${accent}`}>
      <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">
        {title}
      </h3>
      <div className="text-sm leading-relaxed whitespace-pre-line text-foreground">
        {content}
      </div>
    </div>
  );
}

interface Props {
  parsed: ParsedBriefing;
  weekOf: string;
}

export function BriefingSections({ parsed, weekOf }: Props) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold tracking-tight">
            Weekly Briefing
          </CardTitle>
          <span className="text-xs text-muted-foreground">{weekOf}</span>
        </div>
        {parsed.summary && (
          <p className="text-sm text-muted-foreground leading-relaxed">
            {parsed.summary}
          </p>
        )}
      </CardHeader>

      <CardContent className="space-y-5">
        <Section
          title="Financial Alerts"
          content={parsed.financialAlerts}
          accent="border-amber-400 dark:border-amber-500"
        />
        {parsed.financialAlerts && parsed.regulatoryUpdates && <Separator />}
        <Section
          title="Regulatory Updates"
          content={parsed.regulatoryUpdates}
          accent="border-sky-400 dark:border-sky-500"
        />
        {(parsed.financialAlerts || parsed.regulatoryUpdates) &&
          parsed.actions && <Separator />}
        <Section
          title="This Week's Actions"
          content={parsed.actions}
          accent="border-emerald-500 dark:border-emerald-400"
        />
      </CardContent>
    </Card>
  );
}
