import { getExpenseCategories } from "@/lib/api";

interface Props {
  companyId: string;
}

function fmtEuro(n: number): string {
  return `€${Math.round(Math.abs(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;
}

// Hand-picked palette that holds up in dark mode
const COLORS = [
  "bg-sky-500",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-violet-500",
  "bg-rose-500",
  "bg-cyan-500",
  "bg-orange-500",
  "bg-fuchsia-500",
];

export async function ExpenseCategoriesCard({ companyId }: Props) {
  const categories = await getExpenseCategories(companyId, 8);

  if (categories.length === 0) {
    return (
      <div className="border rounded-xl overflow-hidden shadow-sm">
        <div className="px-4 py-3 border-b">
          <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Where your money goes
          </span>
        </div>
        <p className="text-xs text-muted-foreground px-4 py-6 text-center">
          No expense breakdown yet — run a Xero sync first.
        </p>
      </div>
    );
  }

  const totalSpend = categories.reduce((sum, c) => sum + c.total, 0) || 1;

  return (
    <div className="border rounded-xl overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Where your money goes
        </span>
        <span className="text-xs text-muted-foreground tabular-nums">
          {fmtEuro(totalSpend)} total
        </span>
      </div>

      {/* Stacked-bar summary */}
      <div className="flex h-2 w-full">
        {categories.map((c, i) => (
          <div
            key={c.name}
            className={`${COLORS[i % COLORS.length]} h-full`}
            style={{ width: `${(c.total / totalSpend) * 100}%` }}
            title={`${c.name} · ${fmtEuro(c.total)}`}
          />
        ))}
      </div>

      <div className="divide-y">
        {categories.map((c, i) => {
          const pct = (c.total / totalSpend) * 100;
          return (
            <div key={c.name} className="px-4 py-2.5 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className={`h-2.5 w-2.5 rounded-full shrink-0 ${COLORS[i % COLORS.length]}`}
                />
                <span className="text-sm truncate" title={c.name}>
                  {c.name}
                </span>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs text-muted-foreground tabular-nums">
                  {pct.toFixed(0)}%
                </span>
                <span className="text-sm font-medium tabular-nums">
                  {fmtEuro(c.total)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
