"""
Module 5 verification test.

Generates a briefing for the connected demo company. Checks the output
contains all required sections and does not lapse into jargon.

Prerequisites:
  - Modules 1-4 must have run end-to-end at least once
  - At least one financial_snapshots row exists for the company
  - At least one embedded regulation chunk exists

Run with:
    cd prospex/backend
    python tests/test_briefing.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── PASTE YOUR COMPANY ID HERE ──────────────────────────────────────────────
COMPANY_ID = "d130a27a-2923-467f-bcbe-c12a0b98ce1c"
# ────────────────────────────────────────────────────────────────────────────

from agent.briefing import generate_briefing
from db.client      import get_client


JARGON_TERMS = [
    "DSO", "EBITDA", "working capital",
    "regulatory technical standard",
    "current ratio",
    "liquidity ratio",
    "accounts receivable",
]


def main():
    print("\n" + "═" * 60)
    print("  PROSPEX — Module 5 Briefing Test")
    print("═" * 60)

    result = generate_briefing(COMPANY_ID)
    briefing = result["briefing"]

    # ── Check structure ─────────────────────────────────────────────────────
    required = ["FINANCIAL ALERTS", "REGULATORY UPDATES", "THIS WEEK'S ACTIONS"]
    missing  = [s for s in required if s not in briefing]
    if missing:
        print(f"\n⚠️  Missing sections: {missing}")
    else:
        print("\n✅ All required sections present")

    # ── Check Supabase save ─────────────────────────────────────────────────
    saved = (
        get_client().table("briefings")
        .select("id, generated_at, health_score")
        .eq("company_id", COMPANY_ID)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    if saved.data:
        print(f"✅ Saved to Supabase: briefings.id = {saved.data[0]['id']}")
    else:
        print("⚠️  Briefing not found in Supabase")

    # ── Jargon check ────────────────────────────────────────────────────────
    found_jargon = [term for term in JARGON_TERMS if term in briefing]
    if found_jargon:
        print(f"\n⚠️  Jargon detected (should have been translated): {found_jargon}")
    else:
        print("✅ No jargon detected")

    print("\n" + "═" * 60)
    print(f"  Health score: {result['health_score']}")
    print(f"  Data quality: {result['data_quality']['data_quality_score']}/100 "
          f"({result['data_quality']['confidence']})")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
