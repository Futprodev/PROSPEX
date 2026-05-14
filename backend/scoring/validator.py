"""
Pre-scoring data quality check.

The scoring engine needs trustworthy inputs. This validator runs first,
flags missing/impossible values, and produces a data_quality_score.
A low quality score (< 60) means the briefing should show a warning banner
rather than presenting the health score as authoritative.
"""

REQUIRED_FIELDS = [
    "annual_revenue",
    "total_cash",
    "gross_margin_pct",
]

OPTIONAL_FIELDS = [
    "monthly_burn",
    "dso_days",
    "accounts_receivable",
    "total_assets",
    "total_liabilities",
    "operating_expenses",
    "net_profit",
]


def _is_impossible(field, value):
    """Returns a string describing why a value is impossible, or None if OK."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return f"{field} is not a number"

    if field == "annual_revenue" and v < 0:
        return "annual_revenue is negative"
    if field == "gross_margin_pct" and (v > 100 or v < -100):
        return f"gross_margin_pct out of range ({v}%)"
    if field == "total_cash" and v < -1000:
        return "total_cash deeply negative"
    if field == "dso_days" and (v < 0 or v > 365):
        return f"dso_days out of plausible range ({v})"
    return None


def validate_financial_data(parsed_data):
    """
    Inspects the parsed Xero data and returns a quality assessment.

    Returns dict with:
      is_valid           — True if scoring can proceed
      data_quality_score — 0-100 (shown to user alongside health score)
      warnings           — non-blocking issues
      errors             — blocking issues (scoring still proceeds but flagged)
      confidence         — 'high' / 'medium' / 'low'
    """
    warnings = []
    errors   = []

    # Check required fields
    missing_required = [f for f in REQUIRED_FIELDS if parsed_data.get(f) is None]
    for f in missing_required:
        errors.append(f"Missing required field: {f}")

    # Check optional fields
    missing_optional = [f for f in OPTIONAL_FIELDS if parsed_data.get(f) is None]
    for f in missing_optional:
        warnings.append(f"Missing optional field: {f}")

    # Check for impossible values
    all_fields = REQUIRED_FIELDS + OPTIONAL_FIELDS
    for field in all_fields:
        msg = _is_impossible(field, parsed_data.get(field))
        if msg:
            errors.append(msg)

    # Check monthly trend depth
    revenue_trend = parsed_data.get("monthly_revenue_trend") or []
    if len(revenue_trend) < 3:
        warnings.append("Less than 3 months of revenue trend data")

    expense_trend = parsed_data.get("monthly_expense_trend") or []
    if len(expense_trend) < 3:
        warnings.append("Less than 3 months of expense trend data")

    # Cash >> revenue is suspicious
    revenue = parsed_data.get("annual_revenue")
    cash    = parsed_data.get("total_cash")
    if revenue and cash and revenue > 0 and cash > revenue * 10:
        warnings.append("Cash is more than 10x annual revenue — unusual, verify data")

    # Compute data quality score
    total_fields    = len(REQUIRED_FIELDS) + len(OPTIONAL_FIELDS)
    filled_fields   = total_fields - len(missing_required) - len(missing_optional)
    completeness    = (filled_fields / total_fields) * 100

    # Penalty for blocking errors (impossible values)
    impossible_count = len([e for e in errors if "Missing" not in e])
    quality_score = completeness - (impossible_count * 15)
    quality_score = max(0, min(100, quality_score))

    # Confidence band
    if quality_score >= 80:
        confidence = "high"
    elif quality_score >= 60:
        confidence = "medium"
    else:
        confidence = "low"

    # Can we score at all? Need at least the required fields.
    is_valid = len(missing_required) == 0

    return {
        "is_valid":           is_valid,
        "data_quality_score": round(quality_score, 1),
        "warnings":           warnings,
        "errors":             errors,
        "confidence":         confidence,
    }
