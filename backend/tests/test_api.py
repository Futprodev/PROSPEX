"""
Module 6 verification test.

Starts the FastAPI app in a test client and checks that every
endpoint returns the expected status code and shape.

Run with:
    cd prospex/backend
    python tests/test_api.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── PASTE YOUR COMPANY ID HERE ───────────────────────────────────────────────
COMPANY_ID = "c7777254-7d79-4e37-927f-651ddf7d4cbc"
# ────────────────────────────────────────────────────────────────────────────

from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)


def check(label, response, expected_status=200, required_keys=None):
    ok = response.status_code == expected_status
    status = "✅" if ok else "❌"
    print(f"{status} {label} [{response.status_code}]")
    if not ok:
        print(f"   Body: {response.text[:300]}")
        return False
    if required_keys:
        body = response.json()
        missing = [k for k in required_keys if k not in body]
        if missing:
            print(f"   ⚠️  Missing keys: {missing}")
            return False
    return True


def main():
    print("\n" + "═" * 60)
    print("  PROSPEX — Module 6 API Test")
    print("═" * 60)

    results = []

    # Health
    results.append(check(
        "GET /health",
        client.get("/health"),
        required_keys=["status"],
    ))

    # Companies
    results.append(check(
        "GET /companies",
        client.get("/companies"),
        required_keys=["companies"],
    ))

    results.append(check(
        f"GET /companies/{COMPANY_ID}",
        client.get(f"/companies/{COMPANY_ID}"),
        required_keys=["id", "name"],
    ))

    results.append(check(
        "GET /companies/does-not-exist → 404",
        client.get("/companies/does-not-exist"),
        expected_status=404,
    ))

    # Briefings
    results.append(check(
        f"GET /companies/{COMPANY_ID}/briefings",
        client.get(f"/companies/{COMPANY_ID}/briefings"),
        required_keys=["briefings"],
    ))

    results.append(check(
        f"GET /companies/{COMPANY_ID}/briefings/latest",
        client.get(f"/companies/{COMPANY_ID}/briefings/latest"),
        required_keys=["id", "full_briefing", "health_score"],
    ))

    # Manual triggers (just check they accept and queue — don't wait for completion)
    results.append(check(
        f"POST /companies/{COMPANY_ID}/briefings/generate",
        client.post(f"/companies/{COMPANY_ID}/briefings/generate"),
        required_keys=["status"],
    ))

    # Summary
    passed = sum(results)
    total  = len(results)
    print("\n" + "═" * 60)
    print(f"  {passed}/{total} checks passed")
    print("═" * 60 + "\n")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
