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

from fastapi          import APIRouter, HTTPException, BackgroundTasks
from db.client        import get_client

router = APIRouter()


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
