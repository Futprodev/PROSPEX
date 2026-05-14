"""
Module 3 verification test — uses synthetic data only.

Tests four scenarios:
  1. Healthy company        — should score 75-90
  2. Cash crisis            — should score 20-35
  3. Mixed (good margin,
     terrible receivables)  — should produce a mixed score
  4. Missing data           — should fail validation gracefully

Run with:
    cd prospex/backend
    python tests/test_scoring.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.engine    import calculate_scores
from scoring.validator import validate_financial_data


def make_healthy():
    return {
        "annual_revenue":         600_000,
        "cost_of_goods_sold":     180_000,
        "gross_profit":           420_000,
        "gross_margin_pct":       70.0,
        "operating_expenses":     360_000,
        "monthly_burn":           30_000,
        "net_profit":             60_000,
        "total_cash":             480_000,    # 16 months runway
        "total_assets":           650_000,
        "total_liabilities":      200_000,    # current ratio 3.25
        "accounts_receivable":    40_000,
        "accounts_payable":       25_000,
        "overdue_receivables":    2_000,
        "dso_days":               24,
        "monthly_revenue_trend":  [42_000, 45_000, 48_000, 50_000, 52_000, 55_000],
        "monthly_expense_trend":  [28_000, 29_000, 30_000, 30_000, 31_000, 32_000],
    }


def make_cash_crisis():
    return {
        "annual_revenue":         180_000,
        "cost_of_goods_sold":     130_000,
        "gross_profit":           50_000,
        "gross_margin_pct":       28.0,
        "operating_expenses":     220_000,
        "monthly_burn":           18_000,
        "net_profit":             -170_000,
        "total_cash":             18_000,     # 1 month runway
        "total_assets":           45_000,
        "total_liabilities":      90_000,     # underwater
        "accounts_receivable":    50_000,
        "accounts_payable":       45_000,
        "overdue_receivables":    32_000,
        "dso_days":               95,
        "monthly_revenue_trend":  [22_000, 20_000, 18_000, 15_000, 13_000, 11_000],
        "monthly_expense_trend":  [16_000, 17_000, 18_000, 18_000, 19_000, 19_000],
    }


def make_mixed():
    return {
        "annual_revenue":         400_000,
        "cost_of_goods_sold":     100_000,
        "gross_profit":           300_000,
        "gross_margin_pct":       75.0,        # excellent
        "operating_expenses":     280_000,
        "monthly_burn":           23_000,
        "net_profit":             20_000,
        "total_cash":             150_000,     # ~6.5 months
        "total_assets":           260_000,
        "total_liabilities":      180_000,
        "accounts_receivable":    140_000,     # huge AR
        "accounts_payable":       40_000,
        "overdue_receivables":    78_000,
        "dso_days":               128,         # terrible
        "monthly_revenue_trend":  [32_000, 33_000, 34_000, 33_500, 34_000, 34_500],
        "monthly_expense_trend":  [22_000, 23_000, 23_000, 23_500, 23_000, 23_000],
    }


def make_missing():
    return {
        "annual_revenue":         None,
        "gross_margin_pct":       None,
        "total_cash":             None,
        "monthly_burn":           None,
        "dso_days":               None,
        "monthly_revenue_trend":  [],
        "monthly_expense_trend":  [],
    }


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

def print_report(name, data, expected_range):
    print("\n" + "═" * 60)
    print(f"  TEST CASE: {name}")
    print(f"  Expected health score: {expected_range}")
    print("═" * 60)

    quality = validate_financial_data(data)
    print(f"\nData quality: {quality['data_quality_score']}/100  ({quality['confidence']} confidence)")
    if not quality["is_valid"]:
        print("⚠️  Data is not valid for scoring:")
        for err in quality["errors"]:
            print(f"   · {err}")
        return

    if quality["warnings"]:
        print(f"Warnings ({len(quality['warnings'])}):")
        for w in quality["warnings"][:3]:
            print(f"   · {w}")

    result = calculate_scores(data, {"industry": "fintech", "country": "NL"})

    score = result["health_score"]
    print(f"\n→ HEALTH SCORE: {score}/100")

    low, high = expected_range
    in_range = score is not None and low <= score <= high
    print(f"  {'✅' if in_range else '⚠️ '} {'In expected range' if in_range else 'OUTSIDE expected range — review formula'}")

    print(f"\nDimensions:")
    for dim_name, d in result["dimensions"].items():
        score_str = f"{d['score']:.0f}" if d["score"] is not None else "—"
        value_str = f"{d['value']}" if d["value"] is not None else "—"
        print(f"   {dim_name:<18} {score_str:>4}/100  [{d['label']:<8}]  value={value_str}")
        print(f"      → {d['insight']}")

    if result["top_risks"]:
        print(f"\nTop risks ({len(result['top_risks'])}):")
        for i, risk in enumerate(result["top_risks"], 1):
            print(f"   {i}. {risk['dimension']} — {risk['insight']}")

    if result["positive_signals"]:
        print(f"\nPositive signals ({len(result['positive_signals'])}):")
        for i, sig in enumerate(result["positive_signals"], 1):
            print(f"   {i}. {sig['dimension']} — {sig['insight']}")


if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  PROSPEX — Module 3 Scoring Engine Test")
    print("═" * 60)

    print_report("Healthy FinTech",    make_healthy(),     (75, 95))
    print_report("Cash Crisis",         make_cash_crisis(), (5, 25))
    print_report("Mixed (great margin, terrible receivables)", make_mixed(), (45, 70))
    print_report("Missing Data",        make_missing(),     (0, 0))  # won't score

    print("\n" + "═" * 60)
    print("  Review the dimension breakdowns above. If any case scored")
    print("  unexpectedly, the formulas in engine.py need adjustment.")
    print("═" * 60 + "\n")
