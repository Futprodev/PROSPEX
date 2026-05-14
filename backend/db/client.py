import sys
import os

# Allow running this file directly from the backend/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY

_client: Client = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in backend/.env"
            )
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


# Convenience alias used throughout the codebase
supabase_client = get_client


def test_connection():
    """Insert and immediately delete a test row to verify the DB is reachable."""
    try:
        client = get_client()

        # Insert a test company row
        result = (
            client.table("companies")
            .insert({"name": "__test__", "country": "NL", "industry": "test"})
            .execute()
        )

        if not result.data:
            raise RuntimeError("Insert returned no data")

        test_id = result.data[0]["id"]

        # Delete it immediately
        client.table("companies").delete().eq("id", test_id).execute()

        print("✅ Supabase connection working")
        return True

    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False
