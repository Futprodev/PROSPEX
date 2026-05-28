import os
from dotenv import load_dotenv

load_dotenv()

# --- Xero ---
XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET")
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI", "http://localhost:8080/callback")

# --- Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# --- Groq ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- App ---
APP_ENV = os.getenv("APP_ENV", "development")
# Where the OAuth callback should redirect the browser back to after a successful
# Xero connection. Defaults to the local Next.js dev server.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

_REQUIRED = {
    "XERO_CLIENT_ID": (XERO_CLIENT_ID, "Xero developer portal → your app → Client ID"),
    "XERO_CLIENT_SECRET": (XERO_CLIENT_SECRET, "Xero developer portal → your app → Client Secret"),
    "SUPABASE_URL": (SUPABASE_URL, "Supabase dashboard → Settings → API → Project URL"),
    "SUPABASE_ANON_KEY": (SUPABASE_ANON_KEY, "Supabase dashboard → Settings → API → anon public key"),
    "GROQ_API_KEY": (GROQ_API_KEY, "console.groq.com → API Keys → Create key (free)"),
}


def validate_config():
    missing = []
    for name, (value, hint) in _REQUIRED.items():
        if not value or value.endswith("_here"):
            missing.append(f"  ✗ {name}\n      → {hint}")
    if missing:
        lines = "\n".join(missing)
        raise EnvironmentError(
            f"\n\nMissing or unconfigured environment variables in backend/.env:\n{lines}\n"
        )
