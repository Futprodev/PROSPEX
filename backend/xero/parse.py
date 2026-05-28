"""
Xero returns reports as a deeply nested structure:
  Reports[0].Rows[] -> Section rows -> Row[] -> Cells[] -> Value

This file navigates that structure and extracts the specific numbers we need.
All functions return None (not crash) if a field cannot be found.
"""


# ---------------------------------------------------------------------------
# Low-level navigation helpers
# ---------------------------------------------------------------------------

def _get_report(raw_response):
    """Unwraps the outer Reports array."""
    try:
        return raw_response["Reports"][0]
    except (KeyError, IndexError, TypeError):
        return None


def _find_row_by_title(rows, title):
    """
    Recursively searches a Xero rows array for a row whose first cell
    matches `title` (case-insensitive). Returns the row dict or None.
    """
    if not rows:
        return None

    title_lower = title.lower()
    for row in rows:
        cells = row.get("Cells", [])
        if cells and str(cells[0].get("Value", "")).lower() == title_lower:
            return row
        # Recurse into nested Rows (Xero nests sections inside sections)
        nested = _find_row_by_title(row.get("Rows", []), title)
        if nested:
            return nested

    return None


def _find_section_child_rows(rows, section_titles):
    """
    Finds a section row whose title contains any of `section_titles`, and
    returns its direct child Row entries (skipping nested sections/headers).
    Used to enumerate expense categories or per-debtor lines.
    """
    titles_lower = [t.lower() for t in section_titles]
    for row in rows:
        if row.get("RowType") == "Section":
            section_title = row.get("Title", "")
            if not section_title:
                cells = row.get("Cells", [])
                section_title = cells[0].get("Value", "") if cells else ""
            if any(t in section_title.lower() for t in titles_lower):
                return [r for r in row.get("Rows", []) if r.get("RowType") == "Row"]
        # Recurse into nested rows
        nested = _find_section_child_rows(row.get("Rows", []), section_titles)
        if nested:
            return nested
    return []


def _to_float(raw):
    """Robust float parse used across category and debtor parsing."""
    if raw in ("", None):
        return 0.0
    try:
        cleaned = str(raw).replace(",", "").replace(" ", "").strip()
        negative = cleaned.startswith("(") and cleaned.endswith(")")
        cleaned = cleaned.strip("()")
        if cleaned in ("", "-"):
            return 0.0
        v = float(cleaned)
        return -v if negative else v
    except (ValueError, AttributeError):
        return 0.0


def _cell_value(row, cell_index=1):
    """
    Extracts a numeric value from a specific cell in a row.
    Xero often uses cell index 1 for the primary value column.
    Returns float or None.
    """
    if not row:
        return None
    try:
        cells = row.get("Cells", [])
        raw = cells[cell_index].get("Value", "")
        if raw in ("", None):
            return None
        # Strip currency symbols, commas, parentheses (negatives)
        cleaned = str(raw).replace(",", "").replace(" ", "")
        negative = cleaned.startswith("(") and cleaned.endswith(")")
        cleaned  = cleaned.strip("()")
        value    = float(cleaned)
        return -value if negative else value
    except (IndexError, ValueError, AttributeError):
        return None


def _all_cell_values(rows, title):
    """
    Finds a row by title and returns ALL numeric cell values across columns.
    Used for monthly trend data where each column = one month.
    """
    row = _find_row_by_title(rows, title)
    if not row:
        return []

    values = []
    cells  = row.get("Cells", [])
    for cell in cells[1:]:  # skip first cell (it's the label)
        try:
            raw = cell.get("Value", "")
            if raw in ("", None):
                continue
            cleaned  = str(raw).replace(",", "").replace(" ", "")
            negative = cleaned.startswith("(") and cleaned.endswith(")")
            cleaned  = cleaned.strip("()")
            values.append(-float(cleaned) if negative else float(cleaned))
        except (ValueError, AttributeError):
            continue
    return values


# ---------------------------------------------------------------------------
# Monthly-burn calculation (multi-strategy)
# ---------------------------------------------------------------------------

def _compute_monthly_burn(pl_data):
    """
    Returns a monthly burn estimate in EUR/month, or None if no reasonable
    estimate can be produced. Tries, in order:

      1. Average of last 3 non-zero months in monthly_expense_trend
      2. operating_expenses (total) divided by number of non-zero months
      3. (annual_revenue - net_profit) / 12   ← rough proxy if expense row missing
    """
    trend = pl_data.get("monthly_expense_trend") or []
    non_zero = [v for v in trend if v and abs(v) > 0]

    if non_zero:
        recent = non_zero[-3:]
        return round(sum(recent) / len(recent), 2)

    opex = pl_data.get("operating_expenses")
    if opex and opex > 0:
        n_months = len([v for v in trend if v is not None]) or 12
        return round(abs(opex) / n_months, 2)

    revenue = pl_data.get("annual_revenue")
    net     = pl_data.get("net_profit")
    if revenue and net is not None:
        implied_expenses = revenue - net
        if implied_expenses > 0:
            return round(implied_expenses / 12, 2)

    return None


# ---------------------------------------------------------------------------
# P&L parser
# ---------------------------------------------------------------------------

def _parse_pl(pl_raw):
    if not pl_raw:
        return {}, ["P&L report not available"]

    report = _get_report(pl_raw)
    if not report:
        return {}, ["Could not unwrap P&L report"]

    rows   = report.get("Rows", [])
    errors = []
    data   = {}

    # Revenue
    # Xero returns monthly columns in REVERSE chronological order (newest first).
    # Every downstream consumer (burn calc, trend scoring, chart) assumes the
    # opposite, so we reverse here once and everything else works correctly.
    revenue_row = _find_row_by_title(rows, "Total Income") or \
                  _find_row_by_title(rows, "Total Revenue") or \
                  _find_row_by_title(rows, "Income")
    if revenue_row:
        monthly_revenues = list(reversed(
            _all_cell_values(rows, revenue_row["Cells"][0]["Value"])
        ))
        data["monthly_revenue_trend"] = monthly_revenues
        data["annual_revenue"]        = sum(monthly_revenues) if monthly_revenues else None
    else:
        errors.append("annual_revenue: could not find Total Income row")
        data["monthly_revenue_trend"] = []
        data["annual_revenue"]        = None

    # COGS
    cogs_row = _find_row_by_title(rows, "Total Cost of Sales") or \
               _find_row_by_title(rows, "Cost of Sales") or \
               _find_row_by_title(rows, "Total Direct Costs")
    data["cost_of_goods_sold"] = _cell_value(cogs_row) if cogs_row else None
    if not cogs_row:
        errors.append("cost_of_goods_sold: could not find Cost of Sales row")

    # Gross profit
    gp_row = _find_row_by_title(rows, "Gross Profit")
    data["gross_profit"] = _cell_value(gp_row) if gp_row else None

    # Gross margin %
    if data.get("gross_profit") is not None and data.get("annual_revenue"):
        data["gross_margin_pct"] = round(
            data["gross_profit"] / data["annual_revenue"] * 100, 2
        )
    else:
        data["gross_margin_pct"] = None
        errors.append("gross_margin_pct: missing gross_profit or annual_revenue")

    # Operating expenses — Xero's row title varies between localisations and
    # report types, so we try several known headers.
    opex_row = (
        _find_row_by_title(rows, "Total Operating Expenses")
        or _find_row_by_title(rows, "Total Less Operating Expenses")
        or _find_row_by_title(rows, "Less Operating Expenses")
        or _find_row_by_title(rows, "Total Expenses")
        or _find_row_by_title(rows, "Operating Expenses")
    )
    if opex_row:
        # Reverse Xero's newest-first column order so the trend reads
        # oldest → newest, matching the revenue trend and chart.
        monthly_expenses = list(reversed(
            _all_cell_values(rows, opex_row["Cells"][0]["Value"])
        ))
        # Xero sometimes reports expense rows as negative; we want positive
        # outflow figures for the burn calculation and the chart.
        monthly_expenses = [abs(v) for v in monthly_expenses]
        data["monthly_expense_trend"] = monthly_expenses
        data["operating_expenses"]    = sum(monthly_expenses) if monthly_expenses else _cell_value(opex_row)
    else:
        data["monthly_expense_trend"] = []
        data["operating_expenses"]    = None
        errors.append("operating_expenses: could not find Total Expenses row")

    # Monthly burn — average operating expenses over the last 3 months with
    # non-zero data. Empty/zero months are skipped so a half-populated trend
    # doesn't dilute the estimate. Multiple fallbacks if the trend is missing.
    data["monthly_burn"] = _compute_monthly_burn(data)

    # Net profit
    np_row = _find_row_by_title(rows, "Net Profit") or \
             _find_row_by_title(rows, "Profit for the Year") or \
             _find_row_by_title(rows, "Net Income")
    data["net_profit"] = _cell_value(np_row) if np_row else None
    if not np_row:
        errors.append("net_profit: could not find Net Profit row")

    return data, errors


# ---------------------------------------------------------------------------
# Balance Sheet parser
# ---------------------------------------------------------------------------

def _parse_bs(bs_raw):
    if not bs_raw:
        return {}, ["Balance Sheet report not available"]

    report = _get_report(bs_raw)
    if not report:
        return {}, ["Could not unwrap Balance Sheet report"]

    rows   = report.get("Rows", [])
    errors = []
    data   = {}

    # Cash
    cash_row = _find_row_by_title(rows, "Total Bank") or \
               _find_row_by_title(rows, "Bank") or \
               _find_row_by_title(rows, "Cash and Cash Equivalents") or \
               _find_row_by_title(rows, "Cash")
    data["total_cash"] = _cell_value(cash_row) if cash_row else None
    if not cash_row:
        errors.append("total_cash: could not find Bank/Cash row")

    # Total assets
    assets_row = _find_row_by_title(rows, "Total Assets")
    data["total_assets"] = _cell_value(assets_row) if assets_row else None
    if not assets_row:
        errors.append("total_assets: could not find Total Assets row")

    # Total liabilities
    liab_row = _find_row_by_title(rows, "Total Liabilities")
    data["total_liabilities"] = _cell_value(liab_row) if liab_row else None
    if not liab_row:
        errors.append("total_liabilities: could not find Total Liabilities row")

    # Accounts receivable (current asset)
    ar_row = _find_row_by_title(rows, "Accounts Receivable") or \
             _find_row_by_title(rows, "Trade and Other Receivables") or \
             _find_row_by_title(rows, "Debtors")
    data["accounts_receivable"] = _cell_value(ar_row) if ar_row else None

    # Accounts payable
    ap_row = _find_row_by_title(rows, "Accounts Payable") or \
             _find_row_by_title(rows, "Trade and Other Payables") or \
             _find_row_by_title(rows, "Creditors")
    data["accounts_payable"] = _cell_value(ap_row) if ap_row else None

    return data, errors


# ---------------------------------------------------------------------------
# Aged Receivables parser
# ---------------------------------------------------------------------------

def _parse_ar(ar_raw):
    """
    Parses the AgedReceivables summary report.
    Columns: Label | Current | 30 days | 60 days | 90 days | Older | Total
    The summary has one totals row — we find it by looking for the last SummaryRow.
    """
    if not ar_raw:
        return {}, ["Aged Receivables report not available"]

    report = _get_report(ar_raw)
    if not report:
        return {}, ["Could not unwrap Aged Receivables report"]

    rows   = report.get("Rows", [])
    errors = []
    data   = {}

    def to_float(val):
        v = str(val).replace(",", "").strip()
        if v in ("", "-", "0.00", "0"):
            return 0.0
        try:
            return float(v)
        except ValueError:
            return 0.0

    # Find the summary / totals row
    totals_cells = None
    for row in rows:
        if row.get("RowType") in ("SummaryRow", "Row"):
            cells = row.get("Cells", [])
            if cells and str(cells[0].get("Value", "")).lower() in ("total", "totals"):
                totals_cells = cells
                break
        for sub in row.get("Rows", []):
            if sub.get("RowType") in ("SummaryRow",):
                totals_cells = sub.get("Cells", [])
                break

    if totals_cells and len(totals_cells) >= 6:
        # Columns: 0=label, 1=current, 2=30days, 3=60days, 4=90days, 5=older, 6=total (may vary)
        current  = to_float(totals_cells[1].get("Value", 0))
        days_30  = to_float(totals_cells[2].get("Value", 0))
        days_60  = to_float(totals_cells[3].get("Value", 0))
        days_90  = to_float(totals_cells[4].get("Value", 0))
        older    = to_float(totals_cells[5].get("Value", 0)) if len(totals_cells) > 5 else 0.0
        total    = to_float(totals_cells[-1].get("Value", 0))

        overdue  = days_60 + days_90 + older
        data["overdue_receivables"]   = round(overdue, 2)
        data["_ar_total_from_report"] = round(total, 2)
        data["_ar_current"]           = round(current, 2)
        data["_ar_30_days"]           = round(days_30, 2)
    else:
        # Fallback: scan all rows and sum values
        overdue_total = 0.0
        total_ar      = 0.0
        found         = False
        for row in rows:
            for sub_row in row.get("Rows", []) + ([row] if row.get("RowType") == "Row" else []):
                cells = sub_row.get("Cells", [])
                if len(cells) >= 6:
                    overdue_total += to_float(cells[3].get("Value", 0))
                    overdue_total += to_float(cells[4].get("Value", 0))
                    overdue_total += to_float(cells[5].get("Value", 0)) if len(cells) > 6 else 0
                    total_ar      += to_float(cells[-1].get("Value", 0))
                    found = True

        if found:
            data["overdue_receivables"]   = round(overdue_total, 2)
            data["_ar_total_from_report"] = round(total_ar, 2)
        else:
            data["overdue_receivables"]   = None
            data["_ar_total_from_report"] = None
            errors.append("overdue_receivables: could not parse AR summary rows")

    return data, errors


# ---------------------------------------------------------------------------
# Expense category breakdown
# ---------------------------------------------------------------------------

def _parse_expense_categories(pl_raw):
    """
    Enumerates each category row inside the operating-expenses section and
    returns its total spend across the reporting window plus the most recent
    month's value. Used by the dashboard's expense-breakdown card.
    """
    if not pl_raw:
        return []
    report = _get_report(pl_raw)
    if not report:
        return []
    rows = report.get("Rows", [])

    section_rows = _find_section_child_rows(
        rows,
        ["less operating expenses", "operating expenses", "expenses"],
    )

    categories = []
    for r in section_rows:
        cells = r.get("Cells", [])
        if len(cells) < 2:
            continue
        name = cells[0].get("Value", "").strip()
        if not name:
            continue

        # Xero returns monthly columns newest-first. Reverse so [-1] is current.
        monthly = []
        for cell in cells[1:]:
            v = _to_float(cell.get("Value", ""))
            monthly.append(abs(v))
        monthly = list(reversed(monthly))

        if not monthly:
            continue
        non_zero = [v for v in monthly if v > 0]
        if not non_zero:
            continue

        categories.append({
            "name":        name,
            "total":       round(sum(monthly), 2),
            "current":     round(monthly[-1], 2),
            "avg_monthly": round(sum(non_zero) / len(non_zero), 2),
        })

    # Sort by total descending so the biggest spend categories are first
    categories.sort(key=lambda c: c["total"], reverse=True)
    return categories


# ---------------------------------------------------------------------------
# Per-debtor list (Aged Receivables)
# ---------------------------------------------------------------------------

def _parse_debtors(ar_raw):
    """
    Returns a list of debtors with their AR balance broken into aging buckets.
    Skips totals/summary rows.
    """
    if not ar_raw:
        return []
    report = _get_report(ar_raw)
    if not report:
        return []
    rows = report.get("Rows", [])

    debtors = []

    def visit(rs):
        for r in rs:
            row_type = r.get("RowType")
            if row_type == "Row":
                cells = r.get("Cells", [])
                if len(cells) >= 6:
                    name = (cells[0].get("Value", "") or "").strip()
                    if not name or name.lower() in ("total", "totals"):
                        # fall through to recurse into nested rows
                        pass
                    else:
                        current = _to_float(cells[1].get("Value", ""))
                        d30     = _to_float(cells[2].get("Value", ""))
                        d60     = _to_float(cells[3].get("Value", ""))
                        d90     = _to_float(cells[4].get("Value", ""))
                        older   = _to_float(cells[5].get("Value", "")) if len(cells) > 6 else 0.0
                        total   = _to_float(cells[-1].get("Value", ""))
                        if total > 0:
                            debtors.append({
                                "name":           name,
                                "current":        round(current, 2),
                                "overdue_30":     round(d30, 2),
                                "overdue_60":     round(d60, 2),
                                "overdue_90":     round(d90, 2),
                                "overdue_older":  round(older, 2),
                                "overdue_total":  round(d60 + d90 + older, 2),
                                "total":          round(total, 2),
                            })
            visit(r.get("Rows", []))

    visit(rows)
    # Sort by total balance descending — biggest exposure first
    debtors.sort(key=lambda d: d["total"], reverse=True)
    return debtors


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_financial_data(raw_data):
    """
    Takes the output of pull_all() and returns a single clean flat dict
    with all metrics the scoring engine and agent need.

    Never crashes — always returns a dict even if most fields are None.
    parse_errors lists every field that could not be extracted.
    """
    all_errors = []

    pl_data, pl_errors = _parse_pl(raw_data.get("pl"))
    bs_data, bs_errors = _parse_bs(raw_data.get("bs"))
    ar_data, ar_errors = _parse_ar(raw_data.get("ar"))

    all_errors.extend(pl_errors)
    all_errors.extend(bs_errors)
    all_errors.extend(ar_errors)

    # Merge all parsed sections
    result = {}
    result.update(pl_data)
    result.update(bs_data)
    result.update(ar_data)

    # Calculate DSO if we have what we need
    ar_balance = result.get("accounts_receivable") or result.get("_ar_total_from_report")
    revenue    = result.get("annual_revenue")
    if ar_balance and revenue and revenue > 0:
        result["dso_days"] = round((ar_balance / revenue) * 365, 1)
    else:
        result["dso_days"] = None
        all_errors.append("dso_days: missing accounts_receivable or annual_revenue")

    # Monthly net profit trend = revenue - expenses month by month
    rev_trend = result.get("monthly_revenue_trend") or []
    exp_trend = result.get("monthly_expense_trend") or []
    np_trend = []
    for i in range(min(len(rev_trend), len(exp_trend))):
        np_trend.append(round(rev_trend[i] - exp_trend[i], 2))
    result["monthly_net_profit_trend"] = np_trend

    # Snapshot of the current month so the hero strip can render without
    # re-traversing raw_xero_data each time
    result["current_month_revenue"]    = rev_trend[-1] if rev_trend else None
    result["current_month_expenses"]   = exp_trend[-1] if exp_trend else None
    result["current_month_net_profit"] = np_trend[-1]   if np_trend  else None

    # Previous month for MoM comparison
    result["previous_month_revenue"]    = rev_trend[-2] if len(rev_trend) > 1 else None
    result["previous_month_expenses"]   = exp_trend[-2] if len(exp_trend) > 1 else None
    result["previous_month_net_profit"] = np_trend[-2]  if len(np_trend)  > 1 else None

    # Expense category breakdown (current period total + per-month avg)
    result["expense_categories"] = _parse_expense_categories(raw_data.get("pl"))

    # Per-debtor breakdown for the "who owes me" card
    result["debtors"] = _parse_debtors(raw_data.get("ar"))

    result["parse_errors"] = all_errors

    # Store raw data for re-parsing later if needed (not returned to callers directly)
    result["_raw"] = {k: v for k, v in raw_data.items() if k != "_raw"}

    return result
