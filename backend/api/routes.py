"""
FastAPI route definitions.

Endpoints
─────────
GET  /health                                   — liveness check
GET  /companies                                — list all companies
GET  /companies/{company_id}                   — company profile
GET  /companies/{company_id}/briefings         — list past briefings (newest first)
GET  /companies/{company_id}/briefings/latest  — most recent briefing
POST /companies/{company_id}/sync              — trigger Xero pull now
POST /companies/{company_id}/briefings/generate — trigger full pipeline now
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import datetime

from fastapi          import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import RedirectResponse
from pydantic         import BaseModel
from db.client        import get_client

router = APIRouter()

# In-memory PKCE store (state → verifier). Fine for single-process dev.
# Each entry expires after 10 minutes to prevent unbounded growth.
_PKCE_STORE: dict[str, tuple[str, float]] = {}
_PKCE_TTL_SECONDS = 600


def _pkce_put(state: str, verifier: str):
    import time
    _PKCE_STORE[state] = (verifier, time.time() + _PKCE_TTL_SECONDS)
    # Garbage collect anything expired
    now = time.time()
    for k in list(_PKCE_STORE.keys()):
        if _PKCE_STORE[k][1] < now:
            _PKCE_STORE.pop(k, None)


def _pkce_pop(state: str) -> str | None:
    entry = _PKCE_STORE.pop(state, None)
    if not entry:
        return None
    verifier, expiry = entry
    import time
    if expiry < time.time():
        return None
    return verifier


def _validate_uuid(company_id: str):
    """Raises 404 immediately if company_id is not a valid UUID format."""
    try:
        uuid.UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Company not found")


# ── Health ──────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    return {"status": "ok"}


# ── Companies ────────────────────────────────────────────────────────────────

@router.get("/companies")
def list_companies():
    result = (
        get_client()
        .table("companies")
        .select("id, name, industry, country, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return {"companies": result.data or []}


@router.get("/companies/{company_id}")
def get_company(company_id: str):
    _validate_uuid(company_id)
    result = (
        get_client()
        .table("companies")
        .select("*")
        .eq("id", company_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
    return result.data[0]


# ── Briefings ────────────────────────────────────────────────────────────────

@router.get("/companies/{company_id}/briefings")
def list_briefings(company_id: str, limit: int = 10):
    _validate_uuid(company_id)
    result = (
        get_client()
        .table("briefings")
        .select("id, week_of, health_score, generated_at")
        .eq("company_id", company_id)
        .order("generated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"briefings": result.data or []}


@router.get("/companies/{company_id}/briefings/latest")
def get_latest_briefing(company_id: str):
    _validate_uuid(company_id)
    result = (
        get_client()
        .table("briefings")
        .select("*")
        .eq("company_id", company_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No briefing found. Run a sync + generate first."
        )
    return result.data[0]


@router.get("/companies/{company_id}/snapshots/latest")
def get_latest_snapshot_id(company_id: str):
    """
    Lightweight endpoint for polling: returns just the latest snapshot's id
    and pulled_at. Used by the dashboard progress banner to detect when a
    Sync Xero call has finished writing a new row.
    """
    _validate_uuid(company_id)
    result = (
        get_client()
        .table("financial_snapshots")
        .select("id, pulled_at")
        .eq("company_id", company_id)
        .order("pulled_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return {"id": None, "pulled_at": None}
    return result.data[0]


@router.get("/companies/{company_id}/snapshots/latest/monthly")
def get_monthly_trends(company_id: str):
    """
    Returns monthly revenue + operating expenses for the last 11 months from
    the most recent Xero pull. Used by the dashboard revenue/expense chart.
    """
    _validate_uuid(company_id)

    snap = (
        get_client()
        .table("financial_snapshots")
        .select("raw_xero_data, pulled_at")
        .eq("company_id", company_id)
        .order("pulled_at", desc=True)
        .limit(1)
        .execute()
    )
    if not snap.data:
        raise HTTPException(status_code=404, detail="No financial snapshot found")

    raw = snap.data[0].get("raw_xero_data") or {}
    pl_raw = raw.get("pl") or {}

    from xero.parse import parse_financial_data
    parsed = parse_financial_data(raw)

    # Extract month labels from the P&L header row.
    # Xero returns them newest-first — reverse to match the chronological
    # order the parser uses for the revenue/expense trend arrays.
    months = []
    try:
        report = pl_raw.get("Reports", [{}])[0]
        rows = report.get("Rows", [])
        header = next((r for r in rows if r.get("RowType") == "Header"), None)
        if header:
            cells = header.get("Cells", [])
            months = [c.get("Value", "") for c in cells[1:] if c.get("Value")]
            months = list(reversed(months))
    except (KeyError, IndexError, TypeError, AttributeError):
        pass

    revenue  = parsed.get("monthly_revenue_trend") or []
    expenses = parsed.get("monthly_expense_trend") or []

    # Truncate everything to the shortest array so the chart has aligned points
    n = min(len(months), len(revenue), len(expenses)) if months else min(len(revenue), len(expenses))
    if not months:
        # Fallback: synthesise month labels backward from snapshot date
        import datetime
        end = datetime.date.fromisoformat(snap.data[0]["pulled_at"][:10])
        months = []
        for i in range(n):
            m = end.replace(day=1) - datetime.timedelta(days=30 * (n - 1 - i))
            months.append(m.strftime("%b %y"))

    return {
        "months":   months[:n],
        "revenue":  revenue[:n],
        "expenses": expenses[:n],
    }


@router.get("/companies/{company_id}/briefings/{briefing_id}")
def get_briefing(company_id: str, briefing_id: str):
    _validate_uuid(company_id)
    _validate_uuid(briefing_id)
    result = (
        get_client()
        .table("briefings")
        .select("*")
        .eq("company_id", company_id)
        .eq("id", briefing_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return result.data[0]


# ── Manual triggers ──────────────────────────────────────────────────────────

@router.post("/companies/{company_id}/sync")
def sync_xero(company_id: str, background_tasks: BackgroundTasks):
    """
    Pulls the latest Xero data for a company and saves a new snapshot.
    Runs in the background so the HTTP response returns immediately.
    """
    _assert_company_exists(company_id)

    def _do_sync():
        from xero.pull import pull_all
        pull_all(company_id)

    background_tasks.add_task(_do_sync)
    return {"status": "sync started", "company_id": company_id}


@router.post("/companies/{company_id}/briefings/generate")
def generate_briefing(company_id: str, background_tasks: BackgroundTasks):
    """
    Runs the full pipeline (Xero sync + briefing generation) for a company.
    Runs in the background — poll GET /briefings/latest to see the result.
    """
    _assert_company_exists(company_id)

    def _do_generate():
        from scheduler.jobs import run_single
        run_single(company_id)

    background_tasks.add_task(_do_generate)
    return {"status": "generation started", "company_id": company_id}


# ── Benchmarks ───────────────────────────────────────────────────────────────

@router.get("/companies/{company_id}/benchmarks")
def get_benchmarks(company_id: str):
    """
    Returns each scored dimension alongside the industry good/average/poor
    thresholds it was measured against. Used by the dashboard benchmark card.
    """
    _validate_uuid(company_id)

    client = get_client()
    company = (
        client.table("companies").select("*").eq("id", company_id).limit(1).execute().data
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company = company[0]

    snap = (
        client.table("financial_snapshots")
        .select("*")
        .eq("company_id", company_id)
        .order("pulled_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if not snap:
        raise HTTPException(status_code=404, detail="No financial snapshot yet")
    snap = snap[0]

    from scoring.benchmarks import get_benchmark

    industry = company.get("industry", "fintech")
    country  = company.get("country", "NL")

    # Derive a few ratios that aren't stored directly
    cash    = snap.get("cash")
    burn    = snap.get("monthly_burn")
    runway  = snap.get("runway_months")
    if runway is None and cash is not None and burn:
        runway = round(cash / burn, 1) if burn > 0 else None

    items = [
        {
            "key":      "gross_margin_pct",
            "label":    "Gross margin",
            "value":    snap.get("gross_margin_pct"),
            "unit":     "%",
            "higher_is_better": True,
            "thresholds": get_benchmark(industry, country, "gross_margin_pct"),
        },
        {
            "key":      "runway_months",
            "label":    "Runway",
            "value":    runway,
            "unit":     " mo",
            "higher_is_better": True,
            "thresholds": get_benchmark(industry, country, "runway_months"),
        },
        {
            "key":      "dso_days",
            "label":    "Days to get paid",
            "value":    snap.get("dso_days"),
            "unit":     " days",
            "higher_is_better": False,
            "thresholds": get_benchmark(industry, country, "dso_days"),
        },
    ]
    return {
        "industry": industry,
        "country":  country,
        "items":    items,
    }


# ── Cash flow forecast ───────────────────────────────────────────────────────

@router.get("/companies/{company_id}/forecast")
def get_forecast(company_id: str, months: int = 12):
    """
    Simple linear cash projection: starting cash minus monthly burn for N months.
    Returns the projected balance for each month plus the runway-exhaustion month.
    """
    _validate_uuid(company_id)
    months = max(1, min(36, months))

    snap = (
        get_client()
        .table("financial_snapshots")
        .select("cash, monthly_burn, runway_months, pulled_at")
        .eq("company_id", company_id)
        .order("pulled_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if not snap:
        raise HTTPException(status_code=404, detail="No snapshot to forecast from")

    snap = snap[0]
    cash = snap.get("cash") or 0
    burn = snap.get("monthly_burn") or 0

    today = datetime.date.today()
    projection = []
    for i in range(months + 1):
        month_date = (today.replace(day=1) + datetime.timedelta(days=32 * i)).replace(day=1)
        projected = cash - (burn * i)
        projection.append({
            "month":    month_date.strftime("%b %y"),
            "balance":  round(projected, 2),
            "negative": projected < 0,
        })

    exhausted_at = None
    if burn > 0:
        months_until_zero = cash / burn
        if 0 <= months_until_zero <= months:
            d = (today.replace(day=1) + datetime.timedelta(days=32 * int(months_until_zero))).replace(day=1)
            exhausted_at = d.strftime("%b %y")

    return {
        "starting_cash":  cash,
        "monthly_burn":   burn,
        "months":         months,
        "projection":     projection,
        "exhausted_at":   exhausted_at,
    }


# ── Xero connect / reconnect (FastAPI-native OAuth) ──────────────────────────

# State encoding:
#   "<random>.<company_id>" → reconnect: update the named company
#   "<random>.new"          → first connect: look up by tenant_id or create new

@router.get("/xero/connect")
def xero_connect(company_id: str | None = None):
    """
    Returns the Xero authorisation URL.

    Two modes:
    - With company_id → reconnect: the callback updates that company's tokens
    - Without company_id → first connect: the callback creates a new company
      row (or updates an existing one matched by tenant_id)
    """
    from xero.auth import generate_pkce_pair, get_auth_url

    if company_id:
        _validate_uuid(company_id)
        suffix = company_id
    else:
        suffix = "new"

    verifier, challenge = generate_pkce_pair()
    state = f"{uuid.uuid4().hex}.{suffix}"
    _pkce_put(state, verifier)

    auth_url = get_auth_url(challenge, state=state)
    return {"auth_url": auth_url}


@router.get("/xero/callback")
def xero_callback(request: Request):
    """
    Xero redirects here with ?code=...&state=... after the user authorises.
    Exchanges the code for tokens, upserts the company row, sets the active-
    company cookie, and redirects the browser back to the frontend.
    """
    from fastapi.responses import HTMLResponse, RedirectResponse
    from config import FRONTEND_URL

    code  = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    def fail(msg: str, status: int = 400):
        return HTMLResponse(content=f"<h2>{msg}</h2>", status_code=status)

    if error:
        return fail(f"Xero returned: {error}")
    if not code or not state or "." not in state:
        return fail("Missing or malformed state from Xero.")

    _, suffix = state.split(".", 1)
    verifier = _pkce_pop(state)
    if not verifier:
        return fail('Session expired. Please click "Connect Xero" again.')

    try:
        from xero.auth import (
            exchange_code_for_tokens,
            get_tenant_info,
            save_tokens,
        )

        tokens = exchange_code_for_tokens(code, verifier)
        access_token = tokens["access_token"]
        tenant_id, tenant_name = get_tenant_info(access_token)

        client = get_client()

        if suffix == "new":
            # First connect — look up by tenant_id, else insert a fresh row
            existing = (
                client.table("companies")
                .select("id, name")
                .eq("xero_tenant_id", tenant_id)
                .limit(1)
                .execute()
                .data
            )
            if existing:
                company_id = existing[0]["id"]
                # Update name in case the org was renamed in Xero
                client.table("companies").update({"name": tenant_name}).eq("id", company_id).execute()
            else:
                inserted = (
                    client.table("companies")
                    .insert({
                        "name":           tenant_name,
                        "country":        "NL",
                        "industry":       "fintech",
                        "xero_tenant_id": tenant_id,
                    })
                    .execute()
                    .data
                )
                company_id = inserted[0]["id"]
        else:
            # Reconnect — update tokens + tenant_id on the existing row
            company_id = suffix
            client.table("companies").update({
                "xero_tenant_id": tenant_id,
                "name":           tenant_name,
            }).eq("id", company_id).execute()

        save_tokens(company_id, tokens)

        # Redirect back to the dashboard, setting the active-company cookie.
        # Cookies on "localhost" are shared across ports, so the Next.js dev
        # server at :3000 will see this on its next request.
        response = RedirectResponse(url=f"{FRONTEND_URL}/?connected=1", status_code=303)
        response.set_cookie(
            key="prospex_company_id",
            value=company_id,
            max_age=365 * 24 * 60 * 60,
            httponly=False,    # the CompanyMenu reads it client-side for the delete flow
            samesite="lax",
            path="/",
        )
        return response

    except Exception as e:
        return fail(f"Connect failed: {e}", 500)


# ── Delete a company (used for testing / Demo Company resets) ────────────────

@router.delete("/companies/{company_id}")
def delete_company(company_id: str):
    """
    Hard delete. Cascading FKs on briefings and financial_snapshots mean their
    rows go too. After this, the dashboard will show the Connect Xero screen.
    """
    _assert_company_exists(company_id)
    get_client().table("companies").delete().eq("id", company_id).execute()
    return {"status": "deleted", "company_id": company_id}


# ── Ask your data (LLM chat) ─────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str


@router.post("/companies/{company_id}/ask")
def ask_question(company_id: str, payload: AskRequest):
    """
    Single-turn LLM chat over the company's most recent snapshot and briefing.
    No conversation state — each question is independent.
    """
    _assert_company_exists(company_id)

    from agent.chat import answer_question
    answer = answer_question(company_id, payload.question)
    return {"answer": answer}


# ── Internal helpers ─────────────────────────────────────────────────────────

def _assert_company_exists(company_id: str):
    _validate_uuid(company_id)
    result = (
        get_client()
        .table("companies")
        .select("id")
        .eq("id", company_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Company not found")
