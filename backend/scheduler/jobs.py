"""
Weekly briefing job.

Runs every Monday at 07:00 Amsterdam time. For every company in the
database: pulls the latest Xero data, then generates and saves a briefing.

Can also be triggered manually via the API (POST /companies/{id}/briefing/generate).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import get_client


def run_weekly_briefings():
    """
    Entry point called by APScheduler every Monday morning.
    Iterates over all companies and runs the full pipeline for each.
    """
    client = get_client()
    result = client.table("companies").select("id, name").execute()
    companies = result.data or []

    if not companies:
        print("   ℹ️  No companies found — nothing to do")
        return

    print(f"\n🗓  Weekly briefing run — {len(companies)} company/companies")

    success, failed = 0, 0
    for company in companies:
        company_id   = company["id"]
        company_name = company.get("name", company_id)
        try:
            _run_for_company(company_id, company_name)
            success += 1
        except Exception as e:
            print(f"   ❌ {company_name}: {e}")
            failed += 1

    print(f"\n✅ Weekly run complete — {success} succeeded, {failed} failed\n")


def _run_for_company(company_id: str, company_name: str):
    """Full pipeline for one company: Xero sync → briefing."""
    print(f"\n── {company_name} ──────────────────────────────")

    # 1. Pull latest data from Xero
    from xero.pull import pull_all
    print("   Syncing Xero...")
    pull_all(company_id)

    # 2. Generate briefing
    from agent.briefing import generate_briefing
    print("   Generating briefing...")
    generate_briefing(company_id)


def run_single(company_id: str):
    """
    Trigger the full pipeline for a single company.
    Called by the manual API endpoint.
    """
    client = get_client()
    result = (
        client.table("companies")
        .select("id, name")
        .eq("id", company_id)
        .single()
        .execute()
    )
    if not result.data:
        raise ValueError(f"Company {company_id} not found")

    company_name = result.data.get("name", company_id)
    _run_for_company(company_id, company_name)
