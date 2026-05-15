/**
 * Typed API client for the PROSPEX FastAPI backend.
 * Works in both server components (SSR) and client components.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────

export interface Company {
  id: string;
  name: string;
  industry: string;
  country: string;
  activities?: string;
  created_at: string;
}

export interface Briefing {
  id: string;
  company_id: string;
  generated_at: string;
  week_of: string;
  full_briefing: string;
  financial_summary: string;
  regulatory_summary: string;
  action_items: string[];
  health_score: number | null;
}

export interface BriefingListItem {
  id: string;
  week_of: string;
  health_score: number | null;
  generated_at: string;
}

export interface ParsedDimension {
  name: string;
  score: number;
  label: string;
  insight: string;
}

export interface ParsedBriefing {
  summary: string;
  financialAlerts: string;
  regulatoryUpdates: string;
  actions: string;
}

// ── Fetch helpers ──────────────────────────────────────────────────────────

export async function getCompany(id: string): Promise<Company | null> {
  try {
    const res = await fetch(`${API_URL}/companies/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function getLatestBriefing(
  companyId: string
): Promise<Briefing | null> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/briefings/latest`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function getBriefings(
  companyId: string,
  limit = 10
): Promise<BriefingListItem[]> {
  try {
    // Fetch extra to account for duplicates removed after dedup
    const res = await fetch(
      `${API_URL}/companies/${companyId}/briefings?limit=${limit * 4}`,
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    const data = await res.json();
    const all: BriefingListItem[] = data.briefings ?? [];

    // Keep only the most recent entry per week (API returns newest-first)
    const seen = new Set<string>();
    const deduped = all.filter((b) => {
      const key = b.week_of ?? b.generated_at.slice(0, 10);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    return deduped.slice(0, limit);
  } catch {
    return [];
  }
}

export async function getBriefingById(
  companyId: string,
  briefingId: string
): Promise<Briefing | null> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/briefings/${briefingId}`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateBriefing(companyId: string): Promise<boolean> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/briefings/generate`,
      { method: "POST" }
    );
    return res.ok;
  } catch {
    return false;
  }
}

// ── Parsers ────────────────────────────────────────────────────────────────

/**
 * Splits the LLM briefing text into its four named sections.
 * Handles minor variations in header formatting (trailing colon, whitespace).
 */
export function parseBriefingText(text: string): ParsedBriefing {
  const FA  = "FINANCIAL ALERTS";
  const RU  = "REGULATORY UPDATES";
  const ACT = "THIS WEEK'S ACTIONS";

  const faIdx  = text.indexOf(FA);
  if (faIdx === -1) return { summary: text, financialAlerts: "", regulatoryUpdates: "", actions: "" };

  const ruIdx  = text.indexOf(RU,  faIdx);
  const actIdx = text.indexOf(ACT, faIdx);

  const strip = (s: string) => s.replace(/^[:\s]+/, "").trim();

  const summary          = text.slice(0, faIdx).trim();
  const financialAlerts  = strip(text.slice(faIdx + FA.length,  ruIdx  > -1 ? ruIdx  : actIdx > -1 ? actIdx : undefined));
  const regulatoryUpdates = ruIdx > -1 ? strip(text.slice(ruIdx + RU.length,  actIdx > -1 ? actIdx : undefined)) : "";
  const actions           = actIdx > -1 ? strip(text.slice(actIdx + ACT.length)) : "";

  return { summary, financialAlerts, regulatoryUpdates, actions };
}

/**
 * Parses the financial_summary text (written by briefing.py) into structured objects.
 * Input line format: "  - liquidity: 45/100 [fair] — insight here"
 */
export function parseDimensions(financialSummary: string): ParsedDimension[] {
  if (!financialSummary) return [];
  return financialSummary
    .split("\n")
    .map((line) => {
      const m = line.match(/- (.+?):\s*([\d.]+)\/100\s*\[(\w+)\]\s*[—-]\s*(.+)/);
      if (!m) return null;
      return {
        name:    m[1].trim().charAt(0).toUpperCase() + m[1].trim().slice(1),
        score:   parseFloat(m[2]),
        label:   m[3],
        insight: m[4].trim(),
      } as ParsedDimension;
    })
    .filter((d): d is ParsedDimension => d !== null);
}

// ── Style helpers ──────────────────────────────────────────────────────────

export function scoreColor(score: number | null): string {
  if (score == null) return "text-muted-foreground";
  if (score >= 65) return "text-green-600";
  if (score >= 40) return "text-amber-500";
  return "text-red-500";
}

export function scoreBorderColor(score: number | null): string {
  if (score == null) return "border-border";
  if (score >= 65) return "border-emerald-200 dark:border-emerald-800";
  if (score >= 40) return "border-amber-200 dark:border-amber-800";
  return "border-red-200 dark:border-red-800";
}

export function scoreBg(score: number | null): string {
  if (score == null) return "";
  if (score >= 65) return "bg-emerald-50 dark:bg-emerald-950/30";
  if (score >= 40) return "bg-amber-50 dark:bg-amber-950/30";
  return "bg-red-50 dark:bg-red-950/30";
}

export function labelColor(label: string): string {
  switch (label.toLowerCase()) {
    case "good":     return "text-green-700 bg-green-50 border-green-200";
    case "fair":     return "text-amber-700 bg-amber-50 border-amber-200";
    case "poor":     return "text-orange-700 bg-orange-50 border-orange-200";
    case "critical": return "text-red-700 bg-red-50 border-red-200";
    default:         return "text-muted-foreground bg-muted border-border";
  }
}

const MONTHS = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
];

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  } catch {
    return dateStr;
  }
}
