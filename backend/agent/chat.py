"""
"Ask your data" chat handler.

Given a free-form question from the user, builds a tight prompt around the
most recent snapshot + briefing and returns the LLM's answer. Conversation
state is not stored — each call is independent (good enough for the prototype,
keeps Groq free-tier usage low).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client     import get_client
from xero.pull     import get_latest_snapshot
from agent.llm     import get_llm_provider


CHAT_SYSTEM_PROMPT = """You are PROSPEX — a calm, direct financial advisor for a Dutch FinTech SME owner.

You answer questions about the company's own financial data and recent briefing. Rules:
- Answer in plain language. Translate every technical term.
- Never invent numbers. If a number is not in the data below, say "I don't have that data."
- Keep answers under 4 sentences unless the user asks for detail.
- If the question is not about this company's finances or recent regulations, politely redirect.
- Format important numbers with euros (€) and commas. No markdown headers.
"""


def _build_context(company, snapshot, briefing):
    bits = []

    bits.append("COMPANY")
    bits.append(f"  Name: {company.get('name')}")
    bits.append(f"  Industry: {company.get('industry')} · {company.get('country')}")
    bits.append("")

    bits.append("LATEST FINANCIAL SNAPSHOT")
    if snapshot:
        bits.append(f"  Cash: €{snapshot.get('cash') or 0:,.0f}")
        bits.append(f"  Annual revenue: €{snapshot.get('annual_revenue') or 0:,.0f}")
        bits.append(f"  Monthly burn: €{snapshot.get('monthly_burn') or 0:,.0f}")
        bits.append(f"  Runway: {snapshot.get('runway_months') or '—'} months")
        bits.append(f"  Days to get paid (DSO): {snapshot.get('dso_days') or '—'}")
        bits.append(f"  Gross margin: {snapshot.get('gross_margin_pct') or '—'}%")
    else:
        bits.append("  (no snapshot data)")
    bits.append("")

    bits.append("MOST RECENT BRIEFING")
    if briefing:
        bits.append(f"  Health score: {briefing.get('health_score')}/100")
        bits.append(f"  Week of: {briefing.get('week_of')}")
        bits.append("")
        bits.append("  Full briefing text:")
        bits.append("  " + (briefing.get("full_briefing") or "")[:2000].replace("\n", "\n  "))
    else:
        bits.append("  (no briefing yet)")

    return "\n".join(bits)


def answer_question(company_id: str, question: str) -> str:
    """Returns the LLM's answer (or a template fallback) for the user's question."""
    if not question or not question.strip():
        return "Ask me something about your cash, revenue, runway, or the latest briefing."

    client = get_client()

    company = (
        client.table("companies").select("*").eq("id", company_id).limit(1).execute().data
    )
    if not company:
        return "I couldn't find that company in the database."
    company = company[0]

    snapshot = get_latest_snapshot(company_id)

    briefing = (
        client.table("briefings")
        .select("*")
        .eq("company_id", company_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    briefing = briefing[0] if briefing else None

    context = _build_context(company, snapshot, briefing)
    user_prompt = f"{context}\n\nUSER QUESTION:\n{question.strip()}"

    provider = get_llm_provider()
    try:
        return provider.generate(CHAT_SYSTEM_PROMPT, user_prompt).strip()
    except Exception as e:
        return (
            "I couldn't reach the AI service right now. Here's what I can tell you "
            f"from the raw data:\n\n{context[:600]}…"
        )
