import datetime
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xero.auth import refresh_access_token
from db.client import get_client

XERO_API_BASE = "https://api.xero.com/api.xro/2.0"


def _headers(access_token, tenant_id):
    return {
        "Authorization":  f"Bearer {access_token}",
        "Xero-tenant-id": tenant_id,
        "Accept":         "application/json",
    }


def _get_tenant_id(company_id):
    result = get_client().table("companies").select(
        "xero_tenant_id"
    ).eq("id", company_id).single().execute()

    if not result.data or not result.data.get("xero_tenant_id"):
        raise RuntimeError(
            f"No Xero tenant ID found for company {company_id}. "
            "Run the auth flow first: python xero/auth_server.py"
        )
    return result.data["xero_tenant_id"]


# ---------------------------------------------------------------------------
# Individual report pullers
# ---------------------------------------------------------------------------

def _latest_xero_date(company_id, access_token, tenant_id):
    """
    Xero Demo Company has data up to a fixed historical date.
    This finds the most recent date that has actual transaction data
    by checking the last bank transaction date.
    Falls back to today if it can't determine the date.
    """
    try:
        response = requests.get(
            f"{XERO_API_BASE}/BankTransactions",
            headers=_headers(access_token, tenant_id),
            params={"page": 1, "pageSize": 1, "order": "Date DESC"},
            timeout=15,
        )
        if response.status_code == 200:
            txns = response.json().get("BankTransactions", [])
            if txns:
                # Xero date format: /Date(1609459200000+0000)/
                raw = txns[0].get("Date", "")
                import re
                match = re.search(r"/Date\((\d+)", raw)
                if match:
                    ts = int(match.group(1)) / 1000
                    return datetime.date.fromtimestamp(ts)
    except Exception:
        pass
    return datetime.date.today()


def pull_profit_and_loss(company_id):
    """
    Pulls 12 months of P&L from Xero.
    Uses the latest date with actual data — handles Demo Company's fixed date range.
    Returns raw JSON response dict, or None on failure.
    """
    try:
        access_token = refresh_access_token(company_id)
        tenant_id    = _get_tenant_id(company_id)

        end_date   = _latest_xero_date(company_id, access_token, tenant_id)
        start_date = end_date - datetime.timedelta(days=365)

        print(f"   P&L date range: {start_date} → {end_date}")

        response = requests.get(
            f"{XERO_API_BASE}/Reports/ProfitAndLoss",
            headers=_headers(access_token, tenant_id),
            params={
                "fromDate":  start_date.strftime("%Y-%m-%d"),
                "toDate":    end_date.strftime("%Y-%m-%d"),
                "periods":   11,
                "timeframe": "MONTH",
            },
            timeout=30,
        )
        if response.status_code != 200:
            print(f"❌ Failed to pull P&L: {response.status_code} — {response.text[:300]}")
            return None
        print(f"✅ Pulled P&L — {len(response.text):,} chars")
        return response.json()

    except Exception as e:
        print(f"❌ Failed to pull P&L: {e}")
        return None


def pull_balance_sheet(company_id):
    """
    Pulls the Balance Sheet as of the latest date with actual data.
    Returns raw JSON response dict, or None on failure.
    """
    try:
        access_token = refresh_access_token(company_id)
        tenant_id    = _get_tenant_id(company_id)

        end_date = _latest_xero_date(company_id, access_token, tenant_id)

        response = requests.get(
            f"{XERO_API_BASE}/Reports/BalanceSheet",
            headers=_headers(access_token, tenant_id),
            params={"date": end_date.strftime("%Y-%m-%d")},
            timeout=30,
        )
        if response.status_code != 200:
            print(f"❌ Failed to pull Balance Sheet: {response.status_code} — {response.text[:300]}")
            return None
        print(f"✅ Pulled Balance Sheet — {len(response.text):,} chars")
        return response.json()

    except Exception as e:
        print(f"❌ Failed to pull Balance Sheet: {e}")
        return None


def pull_aged_receivables(company_id):
    """
    Pulls aged receivables by contact as of the latest date with actual data.
    Returns raw JSON response dict, or None on failure.
    """
    try:
        access_token = refresh_access_token(company_id)
        tenant_id    = _get_tenant_id(company_id)

        end_date = _latest_xero_date(company_id, access_token, tenant_id)

        response = requests.get(
            f"{XERO_API_BASE}/Reports/AgedReceivables",
            headers=_headers(access_token, tenant_id),
            params={"date": end_date.strftime("%Y-%m-%d")},
            timeout=30,
        )
        if response.status_code != 200:
            print(f"❌ Failed to pull Aged Receivables: {response.status_code} — {response.text[:300]}")
            return None
        print(f"✅ Pulled Aged Receivables — {len(response.text):,} chars")
        return response.json()

    except Exception as e:
        print(f"❌ Failed to pull Aged Receivables: {e}")
        return None


def pull_bank_transactions(company_id):
    """
    Pulls the 100 most recent bank transactions.
    Returns raw JSON response dict, or None on failure.
    """
    try:
        access_token = refresh_access_token(company_id)
        tenant_id    = _get_tenant_id(company_id)

        response = requests.get(
            f"{XERO_API_BASE}/BankTransactions",
            headers=_headers(access_token, tenant_id),
            params={"page": 1, "pageSize": 100},
            timeout=30,
        )
        response.raise_for_status()
        print(f"✅ Pulled Bank Transactions — {len(response.text):,} chars")
        return response.json()

    except Exception as e:
        print(f"❌ Failed to pull Bank Transactions: {e}")
        return None


def pull_all(company_id):
    """
    Calls all four pullers and returns a combined dict.
    If one call fails, logs it and continues — never crashes the whole pipeline.
    """
    print(f"\nPulling all Xero data for company {company_id}...")

    raw = {
        "pl":           pull_profit_and_loss(company_id),
        "bs":           pull_balance_sheet(company_id),
        "ar":           pull_aged_receivables(company_id),
        "transactions": pull_bank_transactions(company_id),
    }

    pulled  = sum(1 for v in raw.values() if v is not None)
    skipped = sum(1 for v in raw.values() if v is None)

    print(f"\n   {pulled}/4 reports pulled successfully"
          + (f", {skipped} failed (check logs above)" if skipped else ""))

    return raw


# ---------------------------------------------------------------------------
# Supabase persistence
# ---------------------------------------------------------------------------

def save_snapshot(company_id, parsed_data):
    """
    Inserts a new row into financial_snapshots with the parsed financial metrics.
    Returns the new snapshot ID.
    """
    row = {
        "company_id":         company_id,
        "annual_revenue":     parsed_data.get("annual_revenue"),
        "gross_margin_pct":   parsed_data.get("gross_margin_pct"),
        "monthly_burn":       parsed_data.get("monthly_burn"),
        "cash":               parsed_data.get("total_cash"),
        "dso_days":           parsed_data.get("dso_days"),
        "top_risks":          [],
        "raw_xero_data":      parsed_data.get("_raw", {}),
    }

    # Calculate runway if we have both cash and burn
    cash  = parsed_data.get("total_cash")
    burn  = parsed_data.get("monthly_burn")
    if cash is not None and burn and burn > 0:
        row["runway_months"] = round(cash / burn, 1)

    result = get_client().table("financial_snapshots").insert(row).execute()

    if not result.data:
        raise RuntimeError("Snapshot insert returned no data")

    snapshot_id = result.data[0]["id"]
    print(f"✅ Saved snapshot to Supabase (id: {snapshot_id})")
    return snapshot_id


def get_latest_snapshot(company_id):
    """Returns the most recent financial snapshot for a company, or None."""
    result = (
        get_client()
        .table("financial_snapshots")
        .select("*")
        .eq("company_id", company_id)
        .order("pulled_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_previous_snapshot(company_id):
    """
    Returns the snapshot from the previous week (second-most-recent).
    Used by the agent to identify what changed since last briefing.
    """
    result = (
        get_client()
        .table("financial_snapshots")
        .select("*")
        .eq("company_id", company_id)
        .order("pulled_at", desc=True)
        .limit(2)
        .execute()
    )
    return result.data[1] if result.data and len(result.data) > 1 else None
