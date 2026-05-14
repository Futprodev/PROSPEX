"""
Development-only Flask server that handles the Xero OAuth2 + PKCE flow.

Run with:
    cd prospex/backend
    python xero/auth_server.py

Then visit: http://localhost:8080/connect

This creates or updates a company record in Supabase and stores the tokens.
Not used in production — the FastAPI app handles this in Module 6.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, redirect, request, session
from config import validate_config
from xero.auth import (
    generate_pkce_pair,
    get_auth_url,
    exchange_code_for_tokens,
    get_tenant_id,
    save_tokens,
)
from db.client import get_client

app = Flask(__name__)
app.secret_key = os.urandom(24)  # session encryption — ephemeral, fine for dev


@app.route("/connect")
def connect():
    """
    Step 1: Generate a PKCE pair, store the verifier in the session,
    and redirect the user to Xero's login page.
    """
    code_verifier, code_challenge = generate_pkce_pair()

    # Store verifier in server-side session so /callback can retrieve it.
    # The challenge goes to Xero; the verifier never leaves the server.
    session["pkce_verifier"] = code_verifier

    auth_url = get_auth_url(code_challenge)
    print(f"\n→ Redirecting to Xero login...\n  {auth_url}\n")
    return redirect(auth_url)


@app.route("/callback")
def callback():
    """
    Step 2: Xero redirects here with ?code=... after the user approves.
    Exchange the code + verifier for tokens, then save to Supabase.
    """
    error = request.args.get("error")
    if error:
        return f"<h2>Xero returned an error: {error}</h2>", 400

    code = request.args.get("code")
    if not code:
        return "<h2>No authorization code in callback. Try /connect again.</h2>", 400

    code_verifier = session.pop("pkce_verifier", None)
    if not code_verifier:
        return (
            "<h2>Session expired or missing. Please start again at /connect.</h2>",
            400,
        )

    try:
        # Exchange code + verifier for tokens
        token_data = exchange_code_for_tokens(code, code_verifier)
        access_token = token_data["access_token"]

        # Find out which Xero organisation was connected
        tenant_id = get_tenant_id(access_token)

        # Create or update the company record in Supabase
        client = get_client()

        existing = (
            client.table("companies")
            .select("id, name")
            .eq("xero_tenant_id", tenant_id)
            .execute()
        )

        if existing.data:
            company_id = existing.data[0]["id"]
            company_name = existing.data[0]["name"]
            client.table("companies").update(
                {"xero_tenant_id": tenant_id}
            ).eq("id", company_id).execute()
            print(f"✅ Updated existing company: {company_name} ({company_id})")
        else:
            result = client.table("companies").insert({
                "name":            "Xero Demo Company",
                "country":         "NL",
                "industry":        "fintech",
                "xero_tenant_id":  tenant_id,
            }).execute()
            company_id = result.data[0]["id"]
            company_name = "Xero Demo Company"
            print(f"✅ Created new company record: {company_name} ({company_id})")

        # Save the tokens
        save_tokens(company_id, token_data)
        print(f"✅ Tokens saved for company {company_id}")
        print(f"\n   company_id = {company_id}")
        print("   → Copy this ID into your test files.\n")

        return f"""
        <h2>✅ Xero connected successfully</h2>
        <p><strong>Company:</strong> {company_name}</p>
        <p><strong>company_id:</strong> <code>{company_id}</code></p>
        <p>Copy the company_id above — you'll need it to run the Module 2 tests.</p>
        <p>You can close this window.</p>
        """

    except Exception as e:
        print(f"❌ OAuth callback failed: {e}")
        return f"<h2>Connection failed</h2><pre>{e}</pre>", 500


if __name__ == "__main__":
    try:
        validate_config()
    except EnvironmentError as e:
        print(e)
        sys.exit(1)

    print("\n" + "═" * 50)
    print("PROSPEX — Xero OAuth2 + PKCE Auth Server")
    print("═" * 50)
    print("Visit: http://localhost:8080/connect")
    print("═" * 50 + "\n")

    app.run(host="0.0.0.0", port=8080, debug=False)
