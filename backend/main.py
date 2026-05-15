"""
PROSPEX backend entry point.

Starts the FastAPI app and the APScheduler weekly job.

Run with:
    cd backend
    uvicorn main:app --reload --port 8000

The scheduler fires every Monday at 07:00 Amsterdam time.
You can also trigger a run manually via the API:
    POST /companies/{company_id}/briefings/generate
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import router
from config import validate_config


# ── Scheduler setup ──────────────────────────────────────────────────────────

def _start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from scheduler.jobs import run_weekly_briefings

    scheduler = BackgroundScheduler(timezone="Europe/Amsterdam")
    scheduler.add_job(
        run_weekly_briefings,
        trigger=CronTrigger(day_of_week="mon", hour=7, minute=0),
        id="weekly_briefings",
        replace_existing=True,
    )
    scheduler.start()
    print("✅ Scheduler started — weekly briefings run every Monday at 07:00 AMS")
    return scheduler


# ── App lifecycle ────────────────────────────────────────────────────────────

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        validate_config()
        print("✅ Config validated")
    except EnvironmentError as e:
        print(e)
        # Don't crash — let the app start so /health still responds

    global _scheduler
    _scheduler = _start_scheduler()

    yield

    # Shutdown
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("Scheduler stopped")


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PROSPEX API",
    description="Financial and regulatory briefing platform for Dutch FinTech SMEs",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the Next.js dev server (port 3000) and any deployed frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# ── Dev convenience ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
