"""
Module 2 verification test.

Before running this you must:
1. Run: python xero/auth_server.py
2. Visit: http://localhost:8080/connect
3. Connect the Xero Demo Company
4. Copy the company_id printed in the terminal and paste it below.

Run with:
    cd prospex/backend
    python tests/test_xero.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── PASTE YOUR COMPANY ID HERE ──────────────────────────────────────────────
COMPANY_ID = "d130a27a-2923-467f-bcbe-c12a0b98ce1c"
# ────────────────────────────────────────────────────────────────────────────

from xero.pull import pull_all, save_snapshot, get_latest_snapshot
from xero.parse import parse_financial_data


def print_section(title):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print('─' * 50)


def main():
    print("\n" + "═" * 50)
    print("  PROSPEX — Module 2 Xero Test")
    print("═" * 50)

    if COMPANY_ID == "PASTE_YOUR_COMPANY_ID_HERE":
        print("\n❌ You need to paste your company_id into this file first.")
        print("   1. Run: python xero/auth_server.py")
        print("   2. Visit: http://localhost:8080/connect")
        print("   3. Copy the company_id and paste it at the top of this file.")
        sys.exit(1)

    # ── Step 1: Pull raw data from Xero ─────────────────────────────────────
    print_section("Step 1: Pull raw Xero data")
    raw = pull_all(COMPANY_ID)

    for key, value in raw.items():
        if value is not None:
            size = len(str(value))
            print(f"   ✅ {key}: {size:,} chars")
        else:
            print(f"   ⚠️  {key}: not available")

    # ── Step 2: Parse into clean metrics ────────────────────────────────────
    print_section("Step 2: Parse financial metrics")
    parsed = parse_financial_data(raw)

    fields = [
        ("annual_revenue",        "€"),
        ("cost_of_goods_sold",    "€"),
        ("gross_profit",          "€"),
        ("gross_margin_pct",      "%"),
        ("operating_expenses",    "€"),
        ("net_profit",            "€"),
        ("total_cash",            "€"),
        ("total_assets",          "€"),
        ("total_liabilities",     "€"),
        ("accounts_receivable",   "€"),
        ("accounts_payable",      "€"),
        ("overdue_receivables",   "€"),
        ("monthly_burn",          "€/mo"),
        ("dso_days",              "days"),
    ]

    for field, unit in fields:
        value = parsed.get(field)
        if value is not None:
            print(f"   ✅ {field:<30} = {value:>12,.2f} {unit}")
        else:
            print(f"   ⚠️  {field:<30} = None")

    trends = {
        "monthly_revenue_trend":  parsed.get("monthly_revenue_trend", []),
        "monthly_expense_trend":  parsed.get("monthly_expense_trend", []),
    }
    for name, trend in trends.items():
        if trend:
            formatted = ", ".join(f"€{v:,.0f}" for v in trend[-6:])
            print(f"   ✅ {name} (last 6): [{formatted}]")
        else:
            print(f"   ⚠️  {name}: not available")

    if parsed.get("parse_errors"):
        print(f"\n   Parse warnings ({len(parsed['parse_errors'])}):")
        for err in parsed["parse_errors"]:
            print(f"     · {err}")

    # ── Step 3: Save to Supabase ─────────────────────────────────────────────
    print_section("Step 3: Save snapshot to Supabase")
    snapshot_id = save_snapshot(COMPANY_ID, parsed)

    # ── Step 4: Retrieve from Supabase ───────────────────────────────────────
    print_section("Step 4: Retrieve snapshot from Supabase")
    snapshot = get_latest_snapshot(COMPANY_ID)

    if snapshot and snapshot["id"] == snapshot_id:
        print(f"   ✅ Retrieved snapshot from Supabase")
        print(f"      id:             {snapshot['id']}")
        print(f"      pulled_at:      {snapshot['pulled_at']}")
        print(f"      annual_revenue: {snapshot.get('annual_revenue')}")
        print(f"      health_score:   {snapshot.get('health_score')} (scored in Module 3)")
    else:
        print("   ❌ Could not retrieve the saved snapshot")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "═" * 50)
    filled  = sum(1 for f, _ in fields if parsed.get(f) is not None)
    total   = len(fields)
    print(f"  {filled}/{total} fields parsed   |   snapshot saved ✅")
    print("═" * 50 + "\n")


if __name__ == "__main__":
    main()
