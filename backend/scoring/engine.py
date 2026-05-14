"""
Financial scoring engine.

Takes parsed Xero data + company profile and returns a structured health report:
- Composite health score (0-100)
- Per-dimension scores with labels and plain-English insights
- Top 3 risks ranked by urgency
- Top 2 positive signals

Scoring philosophy: each dimension is scored against industry benchmarks
on a linear scale anchored to 'poor=20', 'average=60', 'good=90'.
The composite is a weighted average.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.benchmarks import get_benchmark, get_industry_label

# Weights must sum to 1.0
WEIGHTS = {
    "liquidity":       0.25,
    "profitability":   0.20,
    "runway":          0.30,
    "receivables":     0.15,
    "cash_flow_trend": 0.10,
}


# ---------------------------------------------------------------------------
# Score-from-benchmark helper
# ---------------------------------------------------------------------------

def _score_against_benchmark(value, thresholds, lower_is_better=False):
    """
    Maps a raw value to a 0-100 score using linear interpolation between
    'poor', 'average', and 'good' benchmark anchors.
      poor    → 20
      average → 60
      good    → 90
    """
    if value is None or thresholds is None:
        return None

    poor    = thresholds["poor"]
    average = thresholds["average"]
    good    = thresholds["good"]

    if lower_is_better:
        if value <= good:    return 90 + min(10, (good - value) / max(good, 1) * 10)
        if value <= average:
            ratio = (average - value) / max(average - good, 0.001)
            return 60 + ratio * 30
        if value <= poor:
            ratio = (poor - value) / max(poor - average, 0.001)
            return 20 + ratio * 40
        # Worse than poor — let it drop, floor only at 0
        return max(0, 20 - (value - poor) / max(poor, 1) * 15)
    else:
        if value >= good:    return min(100, 90 + (value - good) / max(good, 1) * 10)
        if value >= average:
            ratio = (value - average) / max(good - average, 0.001)
            return 60 + ratio * 30
        if value >= poor:
            ratio = (value - poor) / max(average - poor, 0.001)
            return 20 + ratio * 40
        # Worse than poor — let it drop, floor only at 0
        return max(0, 20 - (poor - value) / max(abs(poor), 1) * 15)


# ---------------------------------------------------------------------------
# Per-dimension scorers
# ---------------------------------------------------------------------------

def _score_liquidity(data, industry, country):
    """Can the company cover its immediate bills?"""
    assets      = data.get("total_assets")
    liabilities = data.get("total_liabilities")
    cash        = data.get("total_cash")
    ap          = data.get("accounts_payable")

    # Current ratio = current assets / current liabilities
    # We approximate using total_assets/total_liabilities since Xero parse
    # doesn't separate current vs long-term yet.
    if assets and liabilities and liabilities > 0:
        current_ratio = assets / liabilities
        thresholds    = get_benchmark(industry, country, "current_ratio")
        score         = _score_against_benchmark(current_ratio, thresholds)
        label         = get_industry_label("current_ratio", current_ratio, industry, country)

        if cash and ap and ap > 0:
            coverage = cash / ap
            insight = (
                f"You have €{cash:,.0f} in cash against €{ap:,.0f} in unpaid bills — "
                f"that covers your bills {coverage:.1f}x over."
                if coverage >= 1 else
                f"You have €{cash:,.0f} in cash but owe €{ap:,.0f} — "
                f"cash covers only {coverage*100:.0f}% of what you owe."
            )
        else:
            insight = f"Assets cover liabilities {current_ratio:.1f}x."

        return {"score": score, "value": round(current_ratio, 2), "label": label, "insight": insight}

    return {"score": None, "value": None, "label": "unknown",
            "insight": "Not enough balance sheet data to assess liquidity."}


def _score_profitability(data, industry, country):
    """How much do you keep from every euro of revenue?"""
    margin = data.get("gross_margin_pct")
    if margin is None:
        return {"score": None, "value": None, "label": "unknown",
                "insight": "Gross margin not available — connect P&L data to assess."}

    thresholds = get_benchmark(industry, country, "gross_margin_pct")
    score      = _score_against_benchmark(margin, thresholds)
    label      = get_industry_label("gross_margin_pct", margin, industry, country)

    benchmark_avg = thresholds["average"]
    if label == "good":
        insight = f"You keep €{margin:.0f} of every €100 in revenue — better than the industry average of €{benchmark_avg:.0f}."
    elif label == "average":
        insight = f"You keep €{margin:.0f} of every €100 in revenue — in line with the industry average."
    else:
        insight = f"You keep only €{margin:.0f} of every €100 in revenue — industry average is €{benchmark_avg:.0f}. Direct costs are eating your margin."

    return {"score": score, "value": round(margin, 1), "label": label, "insight": insight}


def _score_runway(data, industry, country):
    """How many months until cash runs out at current burn rate?"""
    cash = data.get("total_cash")
    burn = data.get("monthly_burn")

    if not cash or not burn or burn <= 0:
        return {"score": None, "value": None, "label": "unknown",
                "insight": "Cannot calculate runway — missing cash or monthly burn data."}

    runway = cash / burn
    thresholds = get_benchmark(industry, country, "runway_months")
    score      = _score_against_benchmark(runway, thresholds)
    label      = get_industry_label("runway_months", runway, industry, country)

    if label == "good":
        insight = f"At current spending of €{burn:,.0f}/month, your cash lasts {runway:.1f} months. You have breathing room."
    elif label == "average":
        insight = f"At current spending of €{burn:,.0f}/month, your cash lasts {runway:.1f} months. Watch this — you'd want to fundraise or grow revenue within the next quarter."
    else:
        insight = f"At current spending of €{burn:,.0f}/month, your cash runs out in {runway:.1f} months. This is the most urgent issue."

    return {"score": score, "value": round(runway, 1), "label": label, "insight": insight}


def _score_receivables(data, industry, country):
    """How long do clients take to pay?"""
    dso = data.get("dso_days")
    if dso is None:
        return {"score": None, "value": None, "label": "unknown",
                "insight": "Cannot calculate how long clients take to pay — missing data."}

    thresholds = get_benchmark(industry, country, "dso_days")
    score      = _score_against_benchmark(dso, thresholds, lower_is_better=True)
    label      = get_industry_label("dso_days", dso, industry, country)
    industry_avg = thresholds["average"]

    overdue = data.get("overdue_receivables")
    overdue_clause = f" Of that, €{overdue:,.0f} is more than 60 days overdue." if overdue else ""

    if label == "good":
        insight = f"Clients pay you in an average of {dso:.0f} days — faster than the industry average of {industry_avg:.0f} days."
    elif label == "average":
        insight = f"Clients take an average of {dso:.0f} days to pay you — in line with the industry average of {industry_avg:.0f} days.{overdue_clause}"
    else:
        insight = (
            f"Clients take an average of {dso:.0f} days to pay you — much slower than the {industry_avg:.0f}-day "
            f"industry average. This is tying up cash in unpaid invoices.{overdue_clause}"
        )

    return {"score": score, "value": round(dso, 1), "label": label, "insight": insight}


def _score_cash_flow_trend(data, industry, country):
    """Is revenue trending up, flat, or down over the last 3 months?"""
    trend = data.get("monthly_revenue_trend") or []
    if len(trend) < 3:
        return {"score": None, "value": None, "label": "unknown",
                "insight": "Need at least 3 months of revenue data to assess trend."}

    recent = trend[-3:]
    first, last = recent[0], recent[-1]
    if first <= 0:
        change_pct = 0 if last <= 0 else 100
    else:
        change_pct = ((last - first) / abs(first)) * 100

    if change_pct >= 10:
        score, label = 90, "good"
        insight = f"Revenue is up {change_pct:.0f}% over the last 3 months (€{first:,.0f} → €{last:,.0f}). Growth is healthy."
    elif change_pct >= -5:
        score, label = 60, "average"
        insight = f"Revenue is roughly flat over the last 3 months ({change_pct:+.0f}%). Not declining, but not growing."
    elif change_pct >= -20:
        score, label = 35, "poor"
        insight = f"Revenue is down {abs(change_pct):.0f}% over the last 3 months (€{first:,.0f} → €{last:,.0f}). Investigate."
    else:
        score, label = 12, "poor"
        insight = f"Revenue has fallen {abs(change_pct):.0f}% over the last 3 months. Urgent — find the cause."

    return {"score": score, "value": round(change_pct, 1), "label": label, "insight": insight}


# ---------------------------------------------------------------------------
# Composite score + risk identification
# ---------------------------------------------------------------------------

def calculate_scores(parsed_data, company):
    """
    Returns the full structured health report described at the top of this file.

    company is a dict with at least 'industry' and 'country' keys.
    """
    industry = (company or {}).get("industry", "fintech")
    country  = (company or {}).get("country", "NL")

    dims = {
        "liquidity":       _score_liquidity(parsed_data, industry, country),
        "profitability":   _score_profitability(parsed_data, industry, country),
        "runway":          _score_runway(parsed_data, industry, country),
        "receivables":     _score_receivables(parsed_data, industry, country),
        "cash_flow_trend": _score_cash_flow_trend(parsed_data, industry, country),
    }

    # Composite = weighted average of dimensions that have a score.
    # Re-normalise weights across only the dimensions we could score.
    total_weight = sum(WEIGHTS[k] for k, d in dims.items() if d["score"] is not None)
    if total_weight > 0:
        composite = sum(
            d["score"] * WEIGHTS[k] for k, d in dims.items() if d["score"] is not None
        ) / total_weight
    else:
        composite = None

    # Risks = dimensions labelled 'poor', ordered by urgency (runway first)
    risk_priority = ["runway", "cash_flow_trend", "liquidity", "receivables", "profitability"]
    top_risks = []
    for dim_name in risk_priority:
        d = dims[dim_name]
        if d["label"] == "poor":
            top_risks.append({"dimension": dim_name, "insight": d["insight"], "value": d["value"]})
        if len(top_risks) >= 3:
            break

    # Positive signals = dimensions labelled 'good'
    positive_signals = []
    for dim_name, d in dims.items():
        if d["label"] == "good":
            positive_signals.append({"dimension": dim_name, "insight": d["insight"], "value": d["value"]})
        if len(positive_signals) >= 2:
            break

    return {
        "health_score":     round(composite, 1) if composite is not None else None,
        "dimensions":       dims,
        "top_risks":        top_risks,
        "positive_signals": positive_signals,
    }
