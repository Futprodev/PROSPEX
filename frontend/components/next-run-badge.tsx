"use client";

import { useEffect, useState } from "react";
import { CalendarClock } from "lucide-react";
import { nextScheduledRun } from "@/lib/api";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function format(d: Date): string {
  const date = `${d.getDate()} ${MONTHS[d.getMonth()]}`;
  return `${date}, 07:00`;
}

/**
 * Shows when the backend APScheduler will next run the weekly briefing
 * (every Monday at 07:00 Amsterdam time). Client-only to avoid SSR drift.
 */
export function NextRunBadge() {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    setLabel(format(nextScheduledRun()));
  }, []);

  if (!label) {
    // Reserve space so the layout doesn't jump on hydrate
    return <span className="text-xs text-muted-foreground/50 hidden sm:inline">·</span>;
  }

  return (
    <span
      className="hidden sm:inline-flex items-center gap-1.5 text-xs text-muted-foreground border rounded-md px-2 py-1"
      title="The backend scheduler runs every Monday at 07:00 Amsterdam time"
    >
      <CalendarClock className="h-3 w-3" />
      Next auto-run: {label}
    </span>
  );
}
