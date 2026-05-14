"""
Industry benchmark lookup tables.

Numbers are based on ECB SAFE Survey averages and typical FinTech SME ranges.
A real product would refine these with actual industry data — for the prototype
these are sensible defaults that produce well-calibrated scores.
"""

BENCHMARKS = {
    "fintech": {
        "NL": {
            "gross_margin_pct":  {"good": 65, "average": 50, "poor": 35},
            "runway_months":     {"good": 12, "average": 6,  "poor": 3},
            "dso_days":          {"good": 30, "average": 45, "poor": 70},
            "current_ratio":     {"good": 2.0, "average": 1.2, "poor": 0.8},
            "net_margin_pct":    {"good": 15, "average": 5,  "poor": -5},
        }
    },
    "saas": {
        "NL": {
            "gross_margin_pct":  {"good": 75, "average": 60, "poor": 45},
            "runway_months":     {"good": 18, "average": 9,  "poor": 4},
            "dso_days":          {"good": 25, "average": 40, "poor": 60},
            "current_ratio":     {"good": 2.0, "average": 1.2, "poor": 0.8},
            "net_margin_pct":    {"good": 20, "average": 8,  "poor": -10},
        }
    },
    # Fallback used if industry/country combo not in the table
    "default": {
        "NL": {
            "gross_margin_pct":  {"good": 50, "average": 35, "poor": 20},
            "runway_months":     {"good": 6,  "average": 3,  "poor": 1.5},
            "dso_days":          {"good": 30, "average": 50, "poor": 75},
            "current_ratio":     {"good": 1.8, "average": 1.1, "poor": 0.7},
            "net_margin_pct":    {"good": 10, "average": 3,  "poor": -5},
        }
    },
}


def get_benchmark(industry, country, metric):
    """
    Returns the threshold dict {good, average, poor} for the given metric.
    Falls back to 'default' industry if the requested combo doesn't exist.
    """
    industry_table = BENCHMARKS.get(industry) or BENCHMARKS["default"]
    country_table  = industry_table.get(country) or industry_table.get("NL")
    return country_table.get(metric)


def get_industry_label(metric, value, industry, country):
    """
    Returns 'good', 'average', or 'poor' based on where the value sits
    relative to the benchmark thresholds.

    For metrics where lower is better (dso_days), the comparison is inverted.
    """
    if value is None:
        return "unknown"

    thresholds = get_benchmark(industry, country, metric)
    if not thresholds:
        return "unknown"

    lower_is_better = metric in ("dso_days",)

    if lower_is_better:
        if value <= thresholds["good"]:    return "good"
        if value <= thresholds["average"]: return "average"
        return "poor"
    else:
        if value >= thresholds["good"]:    return "good"
        if value >= thresholds["average"]: return "average"
        return "poor"
