"""
"Ask your data" chat handler.

Builds a rich, structured prompt around the most recent snapshot + briefing so
the LLM can answer concrete questions ("what's my third-highest expense?",
"who owes me the most?", "which dimension is dragging the score down?").

Supports optional conversation history so the user can ask follow-ups.
"""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client     import get_client
from xero.pull     import get_latest_snapshot
from agent.llm     import get_llm_provider


CHAT_SYSTEM_PROMPT = """You are PROSPEX — a calm, direct financial advisor for a Dutch FinTech SME owner.

You answer questions about the company's own financial data and recent briefing. Rules:
- Answer in plain language. Translate every technical term.
- Use the numbers provided. Do not invent or estimate figures that aren't in the data.
- If a number isn't in the data, say "I don't have that data" briefly and move on.
- Keep answers under 4 sentences unless the user asks for detail or a list.
- When the user follows up with "tell me more", "why", or pronouns like "it/that", continue the prior thread — don't restart.
- Format money with euros (€) and thousands separators (€11,683). No markdown headers.
"""


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

def _fmt_eur(v):
    if v is None:
        return "—"
    return f"€{round(v):,}"


def _build_context(company, snapshot, briefing, dimensions, expense_categories, debtors):
    bits = []

    bits.append("COMPANY")
    bits.append(f"  Name: {company.get('name')}")
    bits.append(f"  Industry: {company.get('industry')} · {company.get('country')}")
    bits.append("")

    bits.append("LATEST FINANCIAL SNAPSHOT")
    if snapshot:
        bits.append(f"  Cash: {_fmt_eur(snapshot.get('cash'))}")
        bits.append(f"  Annual revenue: {_fmt_eur(snapshot.get('annual_revenue'))}")
        bits.append(f"  Monthly burn: {_fmt_eur(snapshot.get('monthly_burn'))}")
        bits.append(f"  Runway: {snapshot.get('runway_months') or '—'} months")
        bits.append(f"  Days to get paid (DSO): {snapshot.get('dso_days') or '—'}")
        bits.append(f"  Gross margin: {snapshot.get('gross_margin_pct') or '—'}%")
    else:
        bits.append("  (no snapshot data)")
    bits.append("")

    if expense_categories:
        bits.append("EXPENSE CATEGORIES (ranked by total spend over the period)")
        for i, c in enumerate(expense_categories[:10], 1):
            bits.append(
                f"  {i}. {c['name']} — total {_fmt_eur(c.get('total'))}, "
                f"this month {_fmt_eur(c.get('current'))}, "
                f"avg {_fmt_eur(c.get('avg_monthly'))}/mo"
            )
        bits.append("")

    if debtors:
        bits.append("TOP DEBTORS (who owes the company money)")
        for i, d in enumerate(debtors[:5], 1):
            line = f"  {i}. {d['name']} — total {_fmt_eur(d.get('total'))}"
            if d.get("overdue_total"):
                line += f", of which {_fmt_eur(d.get('overdue_total'))} is 60+ days overdue"
            bits.append(line)
        bits.append("")

    if dimensions:
        bits.append("FINANCIAL DIMENSIONS (5-area health breakdown)")
        for d in dimensions:
            bits.append(
                f"  - {d['name']}: {d['score']}/100 [{d['label']}] — {d['insight']}"
            )
        bits.append("")

    bits.append("MOST RECENT BRIEFING")
    if briefing:
        bits.append(f"  Health score: {briefing.get('health_score')}/100")
        bits.append(f"  Week of: {briefing.get('week_of')}")
        bits.append("")
        bits.append("  Full briefing text:")
        # Higher cap now that Groq's context window is generous
        bits.append("  " + (briefing.get("full_briefing") or "")[:4000].replace("\n", "\n  "))
    else:
        bits.append("  (no briefing yet)")

    return "\n".join(bits)


# ---------------------------------------------------------------------------
# Dimension parsing — borrowed from the frontend's parseDimensions
# ---------------------------------------------------------------------------

DIM_RE = re.compile(r"-\s*(.+?):\s*([\d.]+)/100\s*\[(\w+)\]\s*[—-]\s*(.+)")


def _parse_dimensions(financial_summary: str):
    """Parses the briefing's per-dimension lines into structured dicts."""
    if not financial_summary:
        return []
    out = []
    for line in financial_summary.splitlines():
        m = DIM_RE.search(line)
        if not m:
            continue
        name, score, label, insight = m.groups()
        out.append({
            "name":    name.strip().capitalize(),
            "score":   float(score),
            "label":   label,
            "insight": insight.strip(),
        })
    return out


# ---------------------------------------------------------------------------
# Snapshot re-parse for expense + debtor data
# ---------------------------------------------------------------------------

def _expense_and_debtors_from_snapshot(snap_row):
    """
    Re-parses the saved raw_xero_data to recover the per-category expense
    breakdown and per-debtor list. These aren't stored as discrete columns.
    """
    raw = (snap_row or {}).get("raw_xero_data") or {}
    if not isinstance(raw, dict) or not raw:
        return [], []
    try:
        from xero.parse import parse_financial_data
        parsed = parse_financial_data(raw)
        return (
            parsed.get("expense_categories") or [],
            parsed.get("debtors") or [],
        )
    except Exception:
        return [], []


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def answer_question(company_id: str, question: str, history=None) -> str:
    """
    Returns the LLM's answer for the user's question.

    history (optional) is a list of {role, content} dicts representing prior
    turns in this conversation. The frontend sends the last few turns so the
    LLM can resolve pronouns ("tell me more about it") and follow-ups.
    """
    if not question or not question.strip():
        return "Ask me something about your cash, revenue, runway, expenses, or the latest briefing."

    client = get_client()

    company = (
        client.table("companies").select("*").eq("id", company_id).limit(1).execute().data
    )
    if not company:
        return "I couldn't find that company in the database."
    company = company[0]

    snapshot = get_latest_snapshot(company_id)
    expense_categories, debtors = _expense_and_debtors_from_snapshot(snapshot)

    briefing_row = (
        client.table("briefings")
        .select("*")
        .eq("company_id", company_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    briefing = briefing_row[0] if briefing_row else None

    dimensions = _parse_dimensions(briefing.get("financial_summary", "")) if briefing else []

    context = _build_context(company, snapshot, briefing, dimensions, expense_categories, debtors)

    # Build the messages array: system prompt + optional history + new question.
    # We send the structured context as the first user turn so the LLM "sees"
    # it once at the top of the conversation and can refer back without us
    # repeating it on every follow-up.
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "user",   "content": f"Here is the data I'm asking about:\n\n{context}"},
        {"role": "assistant", "content": "Got it — I'll answer based on the data above."},
    ]

    # Append prior turns (truncated to the last 12 messages = ~6 Q&A pairs)
    if history:
        # Defensive: ensure entries have correct shape
        recent = []
        for entry in history[-12:]:
            role    = entry.get("role")
            content = entry.get("content")
            if role in ("user", "assistant") and content:
                recent.append({"role": role, "content": content})
        messages.extend(recent)

    messages.append({"role": "user", "content": question.strip()})

    provider = get_llm_provider()
    try:
        # If the provider supports raw message arrays, use it; otherwise fall
        # back to the single-prompt API and inline-format the history.
        if hasattr(provider, "generate_messages"):
            return provider.generate_messages(messages).strip()
        # Single-prompt fallback (TemplateFallback path)
        flat_prompt = "\n\n".join(
            f"[{m['role'].upper()}]\n{m['content']}" for m in messages if m["role"] != "system"
        )
        return provider.generate(CHAT_SYSTEM_PROMPT, flat_prompt).strip()
    except Exception:
        return (
            "I couldn't reach the AI service right now. Here's the relevant data:\n\n"
            f"{context[:800]}…"
        )
