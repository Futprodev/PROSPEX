"""
Briefing generator — the full pipeline for one company.

Steps:
  1. Fetch company profile from Supabase
  2. Fetch latest financial snapshot + previous-week snapshot
  3. Run data validation
  4. Run financial scoring
  5. Retrieve relevant regulation chunks (RAG)
  6. Build the prompt
  7. Call the LLM (Groq, falling back to template)
  8. Validate output structure
  9. Save the briefing to Supabase
 10. Return + print
"""

import sys
import os
import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client          import get_client
from xero.pull          import get_latest_snapshot, get_previous_snapshot
from scoring.validator  import validate_financial_data
from scoring.engine     import calculate_scores
from rag.retriever      import build_regulatory_context
from agent.llm          import get_llm_provider
from agent.prompts      import SYSTEM_PROMPT, BRIEFING_PROMPT_TEMPLATE


REQUIRED_SECTIONS = ["FINANCIAL ALERTS", "REGULATORY UPDATES", "THIS WEEK'S ACTIONS"]


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def _format_dimensions(score_report):
    lines = []
    for name, d in score_report["dimensions"].items():
        if d["score"] is None:
            continue
        lines.append(
            f"  - {name}: {d['score']:.0f}/100 [{d['label']}] — {d['insight']}"
        )
    return "\n".join(lines) if lines else "  (no dimension data available)"


def _format_risks(score_report):
    if not score_report["top_risks"]:
        return "  (no dimensions classified as 'poor')"
    return "\n".join(
        f"  {i}. {r['dimension']} — {r['insight']}"
        for i, r in enumerate(score_report["top_risks"], 1)
    )


def _format_positives(score_report):
    if not score_report["positive_signals"]:
        return "  (no standout positive signals)"
    return "\n".join(
        f"  - {s['dimension']} — {s['insight']}"
        for s in score_report["positive_signals"]
    )


def _format_regulations(reg_chunks):
    if not reg_chunks:
        return "  (no relevant regulatory updates retrieved)"
    lines = []
    for i, chunk in enumerate(reg_chunks[:6], 1):
        title   = chunk.get("title", "")[:100]
        snippet = (chunk.get("full_text") or "")[:300].replace("\n", " ")
        source  = chunk.get("source", "")
        lines.append(f"  [{i}] {source} — {title}\n      {snippet}")
    return "\n".join(lines)


def _format_week_over_week(latest, previous):
    if not previous:
        return "  (no previous snapshot — this is the first week of tracking)"

    def diff_line(label, key, fmt="{:,.0f}", suffix=""):
        old = previous.get(key)
        new = latest.get(key)
        if old is None or new is None:
            return None
        delta = new - old
        sign  = "+" if delta >= 0 else ""
        return f"  - {label}: {fmt.format(new)}{suffix} ({sign}{fmt.format(delta)}{suffix} vs last week)"

    lines = [
        diff_line("cash",            "cash"),
        diff_line("health_score",    "health_score", "{:.1f}"),
        diff_line("annual_revenue",  "annual_revenue"),
        diff_line("dso_days",        "dso_days", "{:.1f}", " days"),
    ]
    return "\n".join(l for l in lines if l) or "  (no comparable fields)"


def _build_prompt(company, snapshot, quality, score_report, reg_chunks, previous_snapshot):
    data_quality_warning = ""
    if quality["data_quality_score"] < 60:
        data_quality_warning = (
            f"DATA QUALITY WARNING — score below {quality['data_quality_score']}/100 "
            f"({quality['confidence']} confidence). Note this in the briefing."
        )

    snapshot_for_template = {
        "annual_revenue": snapshot.get("annual_revenue"),
        "cash":           snapshot.get("cash"),
        "dso_days":       snapshot.get("dso_days"),
        "health_score":   score_report["health_score"],
    }

    return BRIEFING_PROMPT_TEMPLATE.format(
        company_name          = company.get("name", "Unknown company"),
        industry              = company.get("industry", "fintech"),
        country               = company.get("country", "NL"),
        activities            = company.get("activities", "payment services, lending"),
        health_score          = score_report["health_score"] or "N/A",
        data_quality_warning  = data_quality_warning,
        financial_scores      = _format_dimensions(score_report),
        top_risks             = _format_risks(score_report),
        positive_signals      = _format_positives(score_report),
        week_over_week        = _format_week_over_week(snapshot_for_template, previous_snapshot),
        regulatory_context    = _format_regulations(reg_chunks),
    )


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------

def _is_valid_briefing(text):
    if not text or len(text) < 100:
        return False
    return all(section in text for section in REQUIRED_SECTIONS)


# ---------------------------------------------------------------------------
# Snapshot → parsed dict (re-parse from raw_xero_data if available)
# ---------------------------------------------------------------------------

def _snapshot_to_parsed(snapshot):
    """
    Reconstructs a parsed_data-shaped dict from the saved snapshot row.
    We saved most fields directly; trends/raw fields come from raw_xero_data.
    """
    parsed = {
        "annual_revenue":     snapshot.get("annual_revenue"),
        "gross_margin_pct":   snapshot.get("gross_margin_pct"),
        "monthly_burn":       snapshot.get("monthly_burn"),
        "total_cash":         snapshot.get("cash"),
        "dso_days":           snapshot.get("dso_days"),
    }
    raw = snapshot.get("raw_xero_data") or {}
    # If we stored the re-parsable raw blob, re-derive trends and BS/AR fields
    if isinstance(raw, dict):
        from xero.parse import parse_financial_data
        try:
            re_parsed = parse_financial_data(raw)
            for k, v in re_parsed.items():
                parsed.setdefault(k, v)
                if parsed.get(k) is None:
                    parsed[k] = v
        except Exception:
            pass
    return parsed


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_briefing(company_id):
    """Runs the full pipeline. Returns the briefing dict and prints it."""
    client = get_client()

    # 1. Company
    company_result = (
        client.table("companies").select("*").eq("id", company_id).single().execute()
    )
    if not company_result.data:
        raise RuntimeError(f"No company found with id {company_id}")
    company = company_result.data

    # 2. Snapshots
    latest = get_latest_snapshot(company_id)
    if not latest:
        raise RuntimeError(f"No financial snapshot found for company {company_id}. "
                           f"Run the Xero sync first.")
    previous = get_previous_snapshot(company_id)

    parsed = _snapshot_to_parsed(latest)

    # 3. Validate
    quality = validate_financial_data(parsed)

    # 4. Score
    score_report = calculate_scores(parsed, company)

    # 5. RAG
    reg_chunks = build_regulatory_context({
        "industry":   company.get("industry"),
        "country":    company.get("country"),
        "activities": "payment services, lending, compliance reporting",
    })

    # 6. Prompt
    prompt = _build_prompt(company, latest, quality, score_report, reg_chunks, previous)

    # 7. LLM
    provider = get_llm_provider()
    try:
        briefing_text = provider.generate(SYSTEM_PROMPT, prompt)
    except Exception as e:
        print(f"   ⚠️  LLM call failed: {e} — falling back to template")
        from agent.llm import TemplateFallback
        briefing_text = TemplateFallback().generate(SYSTEM_PROMPT, prompt)

    # 8. Validate output
    if not _is_valid_briefing(briefing_text):
        print("   ⚠️  LLM output missing required sections — using template fallback")
        from agent.llm import TemplateFallback
        briefing_text = TemplateFallback().generate(SYSTEM_PROMPT, prompt)

    # 9. Save
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())

    row = {
        "company_id":         company_id,
        "week_of":            monday.isoformat(),
        "health_score":       score_report["health_score"],
        "full_briefing":      briefing_text,
        "financial_summary":  _format_dimensions(score_report),
        "regulatory_summary": _format_regulations(reg_chunks),
        "action_items":       [],  # extracted from briefing text in a later iteration
    }
    client.table("briefings").insert(row).execute()

    # 10. Print + return
    _print_briefing(company, score_report, briefing_text)

    return {
        "briefing":     briefing_text,
        "health_score": score_report["health_score"],
        "data_quality": quality,
    }


def _print_briefing(company, score_report, briefing_text):
    today = datetime.date.today().strftime("%d %B %Y")
    score = score_report["health_score"]
    score_str = f"{score:.0f}/100" if score is not None else "—"

    print("\n" + "═" * 60)
    print(f"PROSPEX WEEKLY BRIEFING — {company.get('name', '')}")
    print(f"Week of {today}")
    print(f"Health Score: {score_str}")
    print("═" * 60 + "\n")
    print(briefing_text)
    print("\n" + "═" * 60)
