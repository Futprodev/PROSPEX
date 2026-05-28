import { getDebtors } from "@/lib/api";

interface Props {
  companyId: string;
}

function fmtEuro(n: number): string {
  const abs = Math.abs(n);
  return `€${Math.round(abs).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;
}

export async function TopDebtorsCard({ companyId }: Props) {
  const debtors = await getDebtors(companyId, 5);

  return (
    <div className="border rounded-xl overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b">
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Who owes you
        </span>
      </div>

      {debtors.length === 0 ? (
        <p className="text-xs text-muted-foreground px-4 py-6 text-center">
          No outstanding receivables found.
          <br />
          <span className="text-[11px]">
            (Xero Demo Company's Aged Receivables endpoint often returns 401.)
          </span>
        </p>
      ) : (
        <div className="divide-y">
          {debtors.map((d) => {
            const totalOverdue = d.overdue_total;
            const overduePct = d.total > 0 ? (totalOverdue / d.total) * 100 : 0;
            const overdueColor =
              overduePct >= 50 ? "text-red-500"
              : overduePct >= 20 ? "text-amber-500"
              : "text-muted-foreground";

            return (
              <div key={d.name} className="px-4 py-3 space-y-1.5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium truncate" title={d.name}>
                    {d.name}
                  </p>
                  <span className="text-sm font-semibold tabular-nums shrink-0">
                    {fmtEuro(d.total)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>
                    Current: <span className="text-foreground tabular-nums">{fmtEuro(d.current)}</span>
                  </span>
                  {totalOverdue > 0 && (
                    <span className={overdueColor}>
                      {fmtEuro(totalOverdue)} overdue 60d+
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
