"""
RAG retriever — embeds a query and asks Postgres for the closest regulation chunks.

Uses a Supabase RPC function `match_regulations` defined in db/schema_rag.sql
because the Python SDK can't express pgvector's `<=>` operator directly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import get_client
from regulations.embedder import _get_model


def _embed_query(query_text):
    model = _get_model()
    vec = model.encode(query_text, normalize_embeddings=True, show_progress_bar=False)
    return vec.tolist()


def retrieve_relevant_regulations(company_profile, query, top_k=5):
    """
    Returns the top_k most semantically similar regulation chunks for the query.

    company_profile: {industry, country, activities}
    query: a string — what you want regulations about
    """
    industry   = company_profile.get("industry", "fintech")
    country    = company_profile.get("country", "NL")
    activities = company_profile.get("activities", "payments lending compliance")

    contextual_query = (
        f"{country} {industry} company. Activities: {activities}. "
        f"Looking for: {query}"
    )

    query_embedding = _embed_query(contextual_query)

    client = get_client()
    try:
        result = client.rpc(
            "match_regulations",
            {
                "query_embedding": query_embedding,
                "match_count":     top_k,
            },
        ).execute()
        return result.data or []
    except Exception as e:
        print(f"   ⚠️  RPC match_regulations failed: {e}")
        # Fallback: return latest relevant items without ranking
        result = (
            client.table("regulation_updates")
            .select("id, source, title, url, full_text, date")
            .eq("is_relevant", True)
            .not_.is_("embedding", "null")
            .order("fetched_at", desc=True)
            .limit(top_k)
            .execute()
        )
        return result.data or []


def build_regulatory_context(company_profile):
    """
    Runs three standard queries and returns the merged, deduplicated chunks.
    This is what the agent module calls when generating a briefing.
    """
    queries = [
        "regulatory obligations and compliance requirements",
        "recent regulatory changes and updates",
        "reporting requirements and deadlines",
    ]

    seen   = set()
    merged = []
    for q in queries:
        for chunk in retrieve_relevant_regulations(company_profile, q, top_k=5):
            key = (chunk.get("title"), chunk.get("full_text", "")[:100])
            if key not in seen:
                seen.add(key)
                merged.append(chunk)

    return merged
