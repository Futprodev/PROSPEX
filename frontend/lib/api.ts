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

/**
 * Lightweight poll helpers used by the progress banner. Both return null on
 * failure or when the row doesn't exist yet (a fresh install with no data).
 */

export interface LatestRef {
  id:         string | null;
  generated_at?: string;
  pulled_at?:    string;
}

export async function getLatestBriefingRef(
  companyId: string
): Promise<LatestRef | null> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/briefings?limit=1`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    const data = await res.json();
    const first = data.briefings?.[0];
    if (!first) return { id: null };
    return { id: first.id, generated_at: first.generated_at };
  } catch {
    return null;
  }
}

export async function getLatestSnapshotRef(
  companyId: string
): Promise<LatestRef | null> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/snapshots/latest`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
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

export interface MonthlyTrends {
  months: string[];
  revenue: number[];
  expenses: number[];
}

export async function getMonthlyTrends(
  companyId: string
): Promise<MonthlyTrends | null> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/snapshots/latest/monthly`,
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

// ── Companies list (multi-company switcher) ────────────────────────────────

export interface CompanyListItem {
  id: string;
  name: string;
  industry?: string;
  country?: string;
}

export async function listCompanies(): Promise<CompanyListItem[]> {
  try {
    const res = await fetch(`${API_URL}/companies`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.companies ?? [];
  } catch {
    return [];
  }
}

// ── Benchmarks ─────────────────────────────────────────────────────────────

export interface BenchmarkItem {
  key: string;
  label: string;
  value: number | null;
  unit: string;
  higher_is_better: boolean;
  thresholds: { good: number; average: number; poor: number } | null;
}

export interface BenchmarkResponse {
  industry: string;
  country: string;
  items: BenchmarkItem[];
}

export async function getBenchmarks(
  companyId: string
): Promise<BenchmarkResponse | null> {
  try {
    const res = await fetch(`${API_URL}/companies/${companyId}/benchmarks`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ── Hero metrics + week-over-week deltas ──────────────────────────────────

export interface HeroMetrics {
  cash:                    number | null;
  cash_delta:              number | null;
  runway_months:           number | null;
  burn:                    number | null;
  burn_delta_pct:          number | null;
  dso_days:                number | null;
  dso_delta:               number | null;
  income_this_month:       number | null;
  income_change_pct:       number | null;
  net_profit_this_month:   number | null;
  net_profit_change_pct:   number | null;
  health_score:            number | null;
  health_score_delta:      number | null;
}

export async function getHeroMetrics(companyId: string): Promise<HeroMetrics | null> {
  try {
    const res = await fetch(`${API_URL}/companies/${companyId}/hero-metrics`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ── Debtors ────────────────────────────────────────────────────────────────

export interface Debtor {
  name:           string;
  current:        number;
  overdue_30:     number;
  overdue_60:     number;
  overdue_90:     number;
  overdue_older:  number;
  overdue_total:  number;
  total:          number;
}

export async function getDebtors(companyId: string, limit = 5): Promise<Debtor[]> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/debtors?limit=${limit}`,
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.debtors ?? [];
  } catch {
    return [];
  }
}

// ── Expense categories ─────────────────────────────────────────────────────

export interface ExpenseCategory {
  name:        string;
  total:       number;
  current:     number;
  avg_monthly: number;
}

export async function getExpenseCategories(
  companyId: string,
  limit = 8
): Promise<ExpenseCategory[]> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/expense-categories?limit=${limit}`,
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.categories ?? [];
  } catch {
    return [];
  }
}

// ── Cash flow forecast ─────────────────────────────────────────────────────

export interface ForecastPoint {
  month: string;
  balance: number;
  negative: boolean;
}

export interface ForecastResponse {
  starting_cash: number;
  monthly_burn: number;
  months: number;
  projection: ForecastPoint[];
  exhausted_at: string | null;
}

export async function getForecast(
  companyId: string,
  months = 12
): Promise<ForecastResponse | null> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/forecast?months=${months}`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ── Xero connect / reconnect ───────────────────────────────────────────────

/**
 * Returns the Xero auth URL. If companyId is provided, the callback updates
 * that company's tokens. If omitted, the callback creates a new company.
 */
export async function getXeroAuthUrl(
  companyId?: string | null
): Promise<string | null> {
  try {
    const url = companyId
      ? `${API_URL}/xero/connect?company_id=${companyId}`
      : `${API_URL}/xero/connect`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    const data = await res.json();
    return data.auth_url ?? null;
  } catch {
    return null;
  }
}

export async function deleteCompany(companyId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/companies/${companyId}`, {
      method: "DELETE",
    });
    return res.ok;
  } catch {
    return false;
  }
}

// ── Ask-your-data chat ─────────────────────────────────────────────────────

export interface ChatHistoryEntry {
  role:    "user" | "assistant";
  content: string;
}

export async function askQuestion(
  companyId: string,
  question:  string,
  history?:  ChatHistoryEntry[]
): Promise<string | null> {
  try {
    const res = await fetch(`${API_URL}/companies/${companyId}/ask`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ question, history: history ?? [] }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.answer ?? null;
  } catch {
    return null;
  }
}

export async function syncXero(companyId: string): Promise<boolean> {
  try {
    const res = await fetch(
      `${API_URL}/companies/${companyId}/sync`,
      { method: "POST" }
    );
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Next Monday at 07:00 Amsterdam time as an ISO-ish string for display.
 * Matches the APScheduler cron in backend/main.py.
 */
export function nextScheduledRun(): Date {
  const now = new Date();
  const next = new Date(now);
  // Days until next Monday (1 = Monday). 0 means today is Monday.
  const day = now.getDay();
  const daysUntilMon = day === 1 ? (now.getHours() < 7 ? 0 : 7) : (8 - day) % 7 || 7;
  next.setDate(now.getDate() + daysUntilMon);
  next.setHours(7, 0, 0, 0);
  return next;
}

// ── Parsers ────────────────────────────────────────────────────────────────

/**
 * Splits the LLM briefing text into its four named sections.
 * Handles minor variations in header formatting (trailing colon, whitespace)
 * and strips stray markdown (## headers, **bold**, etc.) that the model
 * sometimes adds despite the system-prompt rules.
 */
export function parseBriefingText(text: string): ParsedBriefing {
  const FA  = "FINANCIAL ALERTS";
  const RU  = "REGULATORY UPDATES";
  const ACT = "THIS WEEK'S ACTIONS";

  const faIdx  = text.indexOf(FA);
  if (faIdx === -1) {
    return { summary: cleanMarkdown(text), financialAlerts: "", regulatoryUpdates: "", actions: "" };
  }

  const ruIdx  = text.indexOf(RU,  faIdx);
  const actIdx = text.indexOf(ACT, faIdx);

  const strip = (s: string) => cleanMarkdown(s.replace(/^[:\s]+/, ""));

  const summary          = cleanMarkdown(text.slice(0, faIdx));
  const financialAlerts  = strip(text.slice(faIdx + FA.length,  ruIdx  > -1 ? ruIdx  : actIdx > -1 ? actIdx : undefined));
  const regulatoryUpdates = ruIdx > -1 ? strip(text.slice(ruIdx + RU.length,  actIdx > -1 ? actIdx : undefined)) : "";
  const actions           = actIdx > -1 ? strip(text.slice(actIdx + ACT.length)) : "";

  return { summary, financialAlerts, regulatoryUpdates, actions };
}

/**
 * Removes leftover markdown noise from LLM output:
 *   - Standalone "##" / "###" lines (used as separators between sections)
 *   - Leading "#" runs on the first line
 *   - Trailing "#" runs on the last line
 *   - **bold** wrappers (kept text, dropped asterisks)
 */
function cleanMarkdown(s: string): string {
  return s
    .replace(/^\s*#+\s*$/gm, "")     // standalone ## or ### lines
    .replace(/^\s*#+\s+/, "")        // leading "## " on first line
    .replace(/\s*#+\s*$/, "")        // trailing "##" at very end
    .replace(/\*\*(.+?)\*\*/g, "$1") // **bold** → bold
    .replace(/\n{3,}/g, "\n\n")      // collapse runs of blank lines
    .trim();
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
