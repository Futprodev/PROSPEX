"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, AlertCircle, X } from "lucide-react";
import { useTaskProgress } from "./task-progress-provider";

const LABELS = {
  briefing: {
    running: "Generating briefing",
    done:    "Briefing ready",
    stalled: "Briefing is taking longer than expected",
  },
  sync: {
    running: "Syncing Xero",
    done:    "Xero sync complete",
    stalled: "Xero sync is taking longer than expected",
  },
} as const;

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

export function ProgressBanner() {
  const { task, dismiss } = useTaskProgress();
  const [elapsed, setElapsed] = useState(0);

  // Tick the elapsed counter once a second while running
  useEffect(() => {
    if (!task || task.status !== "running") return;
    const tick = () => setElapsed(Date.now() - task.startedAt);
    tick();
    const id = setInterval(tick, 1_000);
    return () => clearInterval(id);
  }, [task]);

  if (!task) return null;

  const label = LABELS[task.kind][task.status];

  const tone =
    task.status === "done"    ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-100"
    : task.status === "stalled" ? "bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-100"
    : "bg-sky-50 dark:bg-sky-950/40 border-sky-200 dark:border-sky-900 text-sky-800 dark:text-sky-100";

  const Icon =
    task.status === "done"    ? CheckCircle2
    : task.status === "stalled" ? AlertCircle
    : Loader2;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`no-print sticky top-[57px] z-[9] border-b ${tone} animate-in slide-in-from-top-2 duration-300`}
    >
      <div className="max-w-6xl mx-auto px-6 py-2 flex items-center gap-3">
        <Icon
          className={`h-4 w-4 shrink-0 ${task.status === "running" ? "animate-spin" : ""}`}
        />
        <span className="text-sm font-medium">{label}</span>
        {task.status === "running" && (
          <span className="text-xs opacity-70 tabular-nums">
            · {formatElapsed(elapsed)} elapsed
          </span>
        )}
        {task.status === "stalled" && (
          <span className="text-xs opacity-70">
            · backend may have errored — check logs and refresh
          </span>
        )}
        <button
          onClick={dismiss}
          className="ml-auto opacity-60 hover:opacity-100 transition-opacity"
          aria-label="Dismiss"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
