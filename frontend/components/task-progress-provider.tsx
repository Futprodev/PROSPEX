"use client";

/**
 * Tracks the in-flight background task (briefing generation or Xero sync)
 * so the UI can show a sticky banner from any page. State is persisted to
 * localStorage, so a page reload mid-generation doesn't lose the indicator,
 * and so other tabs see the same status.
 *
 * Detection is signal-based, not timer-based: we save a "baseline" reference
 * (latest briefing id or latest snapshot id) when the task starts, then poll
 * every 3s until the reference changes server-side.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  getLatestBriefingRef,
  getLatestSnapshotRef,
  type LatestRef,
} from "@/lib/api";

const STORAGE_KEY = "prospex_active_task";

// Maximum time we'll wait before flipping into a "took longer than expected" state.
// Generation usually finishes in 30-45s; sync in 10-20s. If we hit this, something
// likely went wrong on the backend.
const STALL_AFTER_MS = 120_000;

export type TaskKind = "briefing" | "sync";

export interface ActiveTask {
  kind:       TaskKind;
  companyId:  string;
  startedAt:  number; // epoch ms
  baselineId: string | null;
  status:     "running" | "done" | "stalled";
}

interface TaskProgressValue {
  task: ActiveTask | null;
  startBriefing: (companyId: string) => Promise<void>;
  startSync:     (companyId: string) => Promise<void>;
  dismiss:       () => void;
}

const Ctx = createContext<TaskProgressValue | null>(null);

export function useTaskProgress() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useTaskProgress must be used inside <TaskProgressProvider>");
  return v;
}

function readStorage(): ActiveTask | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function writeStorage(t: ActiveTask | null) {
  if (typeof window === "undefined") return;
  if (t) localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
  else   localStorage.removeItem(STORAGE_KEY);
}

async function fetchRef(kind: TaskKind, companyId: string): Promise<LatestRef | null> {
  return kind === "briefing"
    ? getLatestBriefingRef(companyId)
    : getLatestSnapshotRef(companyId);
}

export function TaskProgressProvider({ children }: { children: React.ReactNode }) {
  const [task, setTask] = useState<ActiveTask | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const router = useRouter();

  // ── Hydrate from localStorage on mount + listen for cross-tab changes
  useEffect(() => {
    setTask(readStorage());
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        setTask(e.newValue ? JSON.parse(e.newValue) : null);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // Centralised setter — keep storage and state in sync
  const update = useCallback((t: ActiveTask | null) => {
    setTask(t);
    writeStorage(t);
  }, []);

  // ── Poll while a task is running
  useEffect(() => {
    // Tear down any previous poller
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (!task || task.status !== "running") return;

    const tick = async () => {
      // Stall detection
      if (Date.now() - task.startedAt > STALL_AFTER_MS) {
        update({ ...task, status: "stalled" });
        return;
      }
      const ref = await fetchRef(task.kind, task.companyId);
      const currentId = ref?.id ?? null;
      if (currentId && currentId !== task.baselineId) {
        update({ ...task, status: "done" });
        // Pull fresh data into server components
        router.refresh();
      }
    };

    // Run once immediately so reloads pick up the new state fast,
    // then every 3 seconds
    tick();
    pollRef.current = setInterval(tick, 3_000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [task, update, router]);

  // ── Auto-dismiss the "done" banner after a short delay
  useEffect(() => {
    if (!task || task.status !== "done") return;
    const t = setTimeout(() => update(null), 6_000);
    return () => clearTimeout(t);
  }, [task, update]);

  const startBriefing = useCallback(async (companyId: string) => {
    const ref = await getLatestBriefingRef(companyId);
    update({
      kind:       "briefing",
      companyId,
      startedAt:  Date.now(),
      baselineId: ref?.id ?? null,
      status:     "running",
    });
  }, [update]);

  const startSync = useCallback(async (companyId: string) => {
    const ref = await getLatestSnapshotRef(companyId);
    update({
      kind:       "sync",
      companyId,
      startedAt:  Date.now(),
      baselineId: ref?.id ?? null,
      status:     "running",
    });
  }, [update]);

  const dismiss = useCallback(() => update(null), [update]);

  return (
    <Ctx.Provider value={{ task, startBriefing, startSync, dismiss }}>
      {children}
    </Ctx.Provider>
  );
}
