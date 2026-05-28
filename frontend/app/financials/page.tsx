import {
  getCompany,
  getMonthlyTrends,
  getForecast,
} from "@/lib/api";
import { getActiveCompanyId } from "@/lib/company";
import { RevenueExpenseChart } from "@/components/revenue-expense-chart";
import { CashForecastChart } from "@/components/cash-forecast-chart";
import { HeroMetricsStrip } from "@/components/hero-metrics-strip";
import { WeekDeltasCard } from "@/components/week-deltas-card";
import { TopDebtorsCard } from "@/components/top-debtors-card";
import { ExpenseCategoriesCard } from "@/components/expense-categories-card";
import { ConnectXeroScreen } from "@/components/connect-xero-screen";

/**
 * The financial deep dive. Pure description — what the numbers are. No
 * advisory interpretation; that lives on /briefing.
 *
 * Reading order mirrors how a founder consumes a financial dashboard:
 *  1. Hero strip (5-second glance: am I solvent?)
 *  2. Charts (30 seconds: trends + forecast)
 *  3. Operational breakdowns (2 minutes: where is the money going / coming from)
 */
export default async function FinancialsPage() {
  const companyId = await getActiveCompanyId();
  const company   = companyId ? await getCompany(companyId) : null;

  if (!company) {
    return <ConnectXeroScreen />;
  }

  const [trends, forecast] = await Promise.all([
    getMonthlyTrends(companyId),
    getForecast(companyId, 12),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Financials</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Live data pulled from Xero for {company.name}
        </p>
      </div>

      {/* Hero — the 5-second glance */}
      <HeroMetricsStrip companyId={companyId} />

      {/* What changed — sits right under the hero strip so deltas are visible
          alongside the snapshot they refer to */}
      <WeekDeltasCard companyId={companyId} />

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {trends && trends.months.length > 0 && (
          <RevenueExpenseChart trends={trends} />
        )}
        <CashForecastChart forecast={forecast} />
      </div>

      {/* Operational breakdowns — 50:50 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <ExpenseCategoriesCard companyId={companyId} />
        <TopDebtorsCard companyId={companyId} />
      </div>
    </div>
  );
}
