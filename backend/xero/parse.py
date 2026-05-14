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
    revenue_row = _find_row_by_title(rows, "Total Income") or \
                  _find_row_by_title(rows, "Total Revenue") or \
                  _find_row_by_title(rows, "Income")
    if revenue_row:
        monthly_revenues = _all_cell_values(rows, revenue_row["Cells"][0]["Value"])
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

    # Operating expenses
    opex_row = _find_row_by_title(rows, "Total Operating Expenses") or \
               _find_row_by_title(rows, "Total Expenses") or \
               _find_row_by_title(rows, "Operating Expenses")
    if opex_row:
        monthly_expenses = _all_cell_values(rows, opex_row["Cells"][0]["Value"])
        data["monthly_expense_trend"] = monthly_expenses
        data["operating_expenses"]    = sum(monthly_expenses) if monthly_expenses else _cell_value(opex_row)
    else:
        data["monthly_expense_trend"] = []
        data["operating_expenses"]    = None
        errors.append("operating_expenses: could not find Total Expenses row")

    # Monthly burn = average monthly operating expenses over last 3 months
    if data["monthly_expense_trend"]:
        recent = data["monthly_expense_trend"][-3:]
        data["monthly_burn"] = round(sum(recent) / len(recent), 2)
    else:
        data["monthly_burn"] = None

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

    result["parse_errors"] = all_errors

    # Store raw data for re-parsing later if needed (not returned to callers directly)
    result["_raw"] = {k: v for k, v in raw_data.items() if k != "_raw"}

    return result
