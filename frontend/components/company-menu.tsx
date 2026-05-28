"use client";

import { useEffect, useState } from "react";
import {
  Building2,
  ChevronDown,
  RefreshCw,
  Sparkles,
  Link as LinkIcon,
  Trash2,
  CalendarClock,
} from "lucide-react";
import {
  syncXero,
  generateBriefing,
  getXeroAuthUrl,
  nextScheduledRun,
} from "@/lib/api";
import { DeleteCompanyDialog } from "./delete-company-dialog";
import { useTaskProgress } from "./task-progress-provider";

interface Props {
  companyId:   string;
  companyName: string;
  industry?:   string;
  country?:    string;
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function formatNextRun(d: Date): string {
  return `${d.getDate()} ${MONTHS[d.getMonth()]}, 07:00`;
}

export function CompanyMenu({ companyId, companyName, industry, country }: Props) {
  const [open, setOpen]           = useState(false);
  const [busyKey, setBusyKey]     = useState<null | "sync" | "gen" | "reconnect">(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [nextRun, setNextRun]     = useState<string | null>(null);
  const { task, startBriefing, startSync } = useTaskProgress();

  // Compute next-run client-side to avoid SSR/client drift
  useEffect(() => {
    setNextRun(formatNextRun(nextScheduledRun()));
  }, []);

  // Disable sync/generate buttons if either is already running (banner handles UX)
  const taskRunning = task?.status === "running";

  function closeAfter<T>(fn: () => Promise<T>) {
    return async () => {
      await fn();
      setOpen(false);
    };
  }

  const handleSync = closeAfter(async () => {
    setBusyKey("sync");
    // Capture baseline + show banner BEFORE firing the request so a slow
    // network start still shows immediate feedback
    await startSync(companyId);
    const ok = await syncXero(companyId);
    setBusyKey(null);
    if (!ok) {
      alert("Could not start Xero sync.");
    }
    // Polling in the provider handles completion + router.refresh()
  });

  const handleGenerate = closeAfter(async () => {
    setBusyKey("gen");
    await startBriefing(companyId);
    const ok = await generateBriefing(companyId);
    setBusyKey(null);
    if (!ok) {
      alert("Could not start briefing generation.");
    }
  });

  const handleReconnect = closeAfter(async () => {
    setBusyKey("reconnect");
    const url = await getXeroAuthUrl(companyId);
    setBusyKey(null);
    if (url) {
      window.open(url, "_blank", "noopener");
    } else {
      alert("Could not start Xero reconnect.");
    }
  });

  function openDelete() {
    setOpen(false);
    setDeleteOpen(true);
  }

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-2 text-sm px-2.5 py-1.5 rounded-md border hover:bg-muted/40 transition-colors max-w-[260px]"
        >
          <Building2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <span className="truncate text-left">
            <span className="block leading-tight">{companyName}</span>
            {(industry || country) && (
              <span className="block text-[10px] text-muted-foreground capitalize leading-tight">
                {industry}{industry && country ? " · " : ""}{country}
              </span>
            )}
          </span>
          <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
        </button>

        {open && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
            <div className="absolute right-0 mt-1 min-w-[260px] z-50 border rounded-md bg-background shadow-md overflow-hidden">

              {/* Scheduler info */}
              {nextRun && (
                <div className="px-3 py-2 border-b flex items-center gap-2 text-xs text-muted-foreground">
                  <CalendarClock className="h-3 w-3" />
                  <span>Next auto-run: <span className="text-foreground font-medium">{nextRun}</span></span>
                </div>
              )}

              {/* Actions */}
              <button
                onClick={handleSync}
                disabled={busyKey !== null || taskRunning}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted/60 transition-colors disabled:opacity-50 text-left"
                title={taskRunning ? "Another job is running — see the banner" : undefined}
              >
                <RefreshCw className={`h-3.5 w-3.5 text-muted-foreground ${busyKey === "sync" || task?.kind === "sync" && taskRunning ? "animate-spin" : ""}`} />
                {task?.kind === "sync" && taskRunning ? "Syncing…" : "Sync Xero"}
              </button>

              <button
                onClick={handleGenerate}
                disabled={busyKey !== null || taskRunning}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted/60 transition-colors disabled:opacity-50 text-left"
                title={taskRunning ? "Another job is running — see the banner" : undefined}
              >
                <Sparkles className={`h-3.5 w-3.5 text-muted-foreground ${task?.kind === "briefing" && taskRunning ? "animate-pulse" : ""}`} />
                {task?.kind === "briefing" && taskRunning ? "Generating…" : "Generate briefing"}
              </button>

              <button
                onClick={handleReconnect}
                disabled={busyKey !== null}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted/60 transition-colors disabled:opacity-50 text-left"
              >
                <LinkIcon className="h-3.5 w-3.5 text-muted-foreground" />
                {busyKey === "reconnect" ? "Opening…" : "Reconnect Xero"}
              </button>

              <div className="border-t" />

              <button
                onClick={openDelete}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors text-red-600 text-left"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete company
              </button>
            </div>
          </>
        )}
      </div>

      <DeleteCompanyDialog
        companyId={companyId}
        companyName={companyName}
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
      />
    </>
  );
}
