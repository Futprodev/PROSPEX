import hashlib
import base64
import os
import secrets
import time
import datetime
import requests
from urllib.parse import urlencode

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import XERO_CLIENT_ID, XERO_CLIENT_SECRET, XERO_REDIRECT_URI
from db.client import get_client

XERO_AUTH_URL   = "https://login.xero.com/identity/connect/authorize"
XERO_TOKEN_URL  = "https://identity.xero.com/connect/token"
XERO_TENANT_URL = "https://api.xero.com/connections"

SCOPES = " ".join([
    "openid",
    "profile",
    "email",
    "accounting.reports.profitandloss.read",
    "accounting.reports.balancesheet.read",
    "accounting.reports.aged.read",
    "accounting.banktransactions.read",
    "offline_access",
])


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def generate_pkce_pair():
    """
    Returns (code_verifier, code_challenge).

    code_verifier  — random 64-char URL-safe string, stored server-side
    code_challenge — base64url(SHA-256(verifier)), sent to Xero in the auth URL
    """
    code_verifier = secrets.token_urlsafe(48)  # 64 chars after base64url encoding

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge


# ---------------------------------------------------------------------------
# Step 1 — Build the authorization URL
# ---------------------------------------------------------------------------

def get_auth_url(code_challenge, state=None):
    """
    Returns the Xero login URL to redirect the user to.
    Include code_challenge (not the verifier — never send the verifier here).
    """
    params = {
        "response_type":         "code",
        "client_id":             XERO_CLIENT_ID,
        "redirect_uri":          XERO_REDIRECT_URI,
        "scope":                 SCOPES,
        "code_challenge":        code_challenge,
        "code_challenge_method": "S256",
    }
    if state:
        params["state"] = state

    url = f"{XERO_AUTH_URL}?{urlencode(params)}"
    print(f"\n[DEBUG] Auth URL:\n  {url}\n")
    return url


# ---------------------------------------------------------------------------
# Step 2 — Exchange authorization code for tokens
# ---------------------------------------------------------------------------

def exchange_code_for_tokens(code, code_verifier):
    """
    Called from the /callback route after Xero redirects back.
    Sends the authorization code + original verifier to get access/refresh tokens.
    Returns the token dict on success, raises on failure.
    """
    response = requests.post(
        XERO_TOKEN_URL,
        auth=(XERO_CLIENT_ID, XERO_CLIENT_SECRET),
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  XERO_REDIRECT_URI,
            "code_verifier": code_verifier,  # Xero verifies this matches the challenge
        },
        timeout=15,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Token exchange failed ({response.status_code}): {response.text}"
        )

    return response.json()


# ---------------------------------------------------------------------------
# Step 3 — Get the Xero tenant ID for the connected organisation
# ---------------------------------------------------------------------------

def get_tenant_id(access_token):
    """
    After getting tokens, call the connections endpoint to find out which
    Xero organisation (tenant) the user connected. Returns the first tenant ID.
    """
    response = requests.get(
        XERO_TENANT_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Could not retrieve tenant ({response.status_code}): {response.text}"
        )

    tenants = response.json()
    if not tenants:
        raise RuntimeError("No Xero organisations found for this account.")

    return tenants[0]["tenantId"]


# ---------------------------------------------------------------------------
# Step 4 — Save tokens to Supabase
# ---------------------------------------------------------------------------

def save_tokens(company_id, token_data):
    """
    Persists the access token, refresh token, and expiry time for a company.
    Call this after exchange_code_for_tokens() and after every refresh.
    """
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(
        seconds=token_data.get("expires_in", 1800)
    )

    get_client().table("companies").update({
        "xero_access_token":  token_data["access_token"],
        "xero_refresh_token": token_data["refresh_token"],
        "token_expires_at":   expires_at.isoformat() + "Z",
    }).eq("id", company_id).execute()


# ---------------------------------------------------------------------------
# Step 5 — Refresh the access token when it's near expiry
# ---------------------------------------------------------------------------

def refresh_access_token(company_id):
    """
    Checks if the stored token expires within 5 minutes.
    If yes, calls the Xero refresh endpoint and updates Supabase.
    Returns a valid access token.

    Always call this before any Xero API request — never assume the token is valid.
    """
    client = get_client()
    result = client.table("companies").select(
        "xero_access_token, xero_refresh_token, token_expires_at"
    ).eq("id", company_id).single().execute()

    if not result.data:
        raise RuntimeError(f"Company {company_id} not found in database.")

    row = result.data
    raw_expiry = row.get("token_expires_at")
    if raw_expiry:
        expires_at = datetime.datetime.fromisoformat(raw_expiry.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
    else:
        expires_at = datetime.datetime.now(datetime.timezone.utc)
        now = expires_at

    # If the token is still valid for more than 5 minutes, use it as-is
    if (expires_at - now).total_seconds() > 300:
        return row["xero_access_token"]

    # Token is expiring — refresh it
    refresh_token = row["xero_refresh_token"]
    if not refresh_token:
        raise RuntimeError(
            f"No refresh token stored for company {company_id}. "
            "The user needs to reconnect their Xero account."
        )

    response = requests.post(
        XERO_TOKEN_URL,
        auth=(XERO_CLIENT_ID, XERO_CLIENT_SECRET),
        data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=15,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Token refresh failed ({response.status_code}): {response.text}"
        )

    token_data = response.json()
    save_tokens(company_id, token_data)
    return token_data["access_token"]
