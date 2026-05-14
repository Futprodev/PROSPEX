"""
FinTech SME relevance filter.

Most EU regulatory output targets supervisors and large institutions, not SMEs.
This filter encodes domain knowledge about what an SME founder should care about:

  Tier 1 — Direct compliance (hard-allow):
    GDPR, AML/AMLR, DORA, MiCA, PSD2 — affect almost every Dutch FinTech SME.

  Tier 2 — Indirect / supply-chain pressure:
    EU Taxonomy, CSRD, ESG reporting — customers may demand alignment.

  Tier 3 — Procedural noise (hard-reject when from EBA/ESMA without SME-specific framing):
    RTS, ITS, technical standards, peer reviews, supervisory consultations,
    convergence opinions — written for supervisors, not businesses.

A briefing that flags 12 EBA technical standards trains the user to ignore it.
We'd rather miss a borderline item than swamp the briefing with noise.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import get_client

# Tier 1: always relevant. Strong direct compliance signal.
TIER_1_KEYWORDS = [
    "gdpr", "general data protection",
    "aml", "amld", "amlr", "anti-money laundering", "money laundering",
    "dora", "digital operational resilience",
    "mica", "markets in crypto-asset", "crypto-asset",
    "psd2", "payment services directive",
    "kyc", "customer due diligence",
]

# Tier 2: indirect / supply-chain ESG pressure.
TIER_2_KEYWORDS = [
    "eu taxonomy", "taxonomy regulation",
    "csrd", "sustainability reporting",
    "sfdr", "esg disclosure",
]

# Procedural noise — strongly demote when paired with EBA/ESMA/EIOPA sources.
PROCEDURAL_NOISE = [
    "technical standard",
    "regulatory technical standard",   # RTS
    "implementing technical standard", # ITS
    "rts on", "its on",
    "peer review",
    "supervisory consultation",
    "convergence opinion",
    "opinion on",
    "draft guidelines",
    "consultation paper",
    "discussion paper",
    "call for advice",
    "letter to the european commission",
]

# Hard exclude: clearly unrelated domains.
HARD_EXCLUDE = [
    "border management", "visa", "migration",
    "agriculture", "fisheries", "fishery", "veterinary", "plant health",
    "aviation", "shipping", "maritime",
    "defence", "military", "armed forces", "space",
    "education", "schools",
]

# SME-relevant business types — used to rescue EBA/ESMA items that DO target SMEs.
SME_ENTITY_TERMS = [
    "payment institution", "e-money institution", "electronic money",
    "crypto-asset service provider", "casp",
    "small and medium", "sme",
    "fintech", "neobank",
]


def classify(title, full_text):
    """
    Returns (is_relevant: bool, tier: str, reason: str).
    tier ∈ {"tier_1", "tier_2", "tier_3_noise", "off_topic"}.
    """
    t = (title or "").lower()
    b = (full_text or "")[:3000].lower()
    blob = t + " " + b

    # Hard exclude first
    for kw in HARD_EXCLUDE:
        if kw in t:
            return False, "off_topic", f"hard-excluded: '{kw}' in title"

    # Tier 1 wins immediately — these always matter
    for kw in TIER_1_KEYWORDS:
        if kw in blob:
            return True, "tier_1", f"direct compliance: '{kw}'"

    # Tier 2 — supply-chain ESG pressure
    for kw in TIER_2_KEYWORDS:
        if kw in blob:
            return True, "tier_2", f"indirect/supply-chain: '{kw}'"

    # Procedural noise check (only demote if no Tier 1/2 signal was found above)
    has_procedural_marker = any(kw in t for kw in PROCEDURAL_NOISE)
    if has_procedural_marker:
        # Rescue if it explicitly addresses SME entity types
        if any(term in blob for term in SME_ENTITY_TERMS):
            return True, "tier_2", "procedural but addresses SME entities"
        return False, "tier_3_noise", "procedural standard for supervisors"

    # No clear signal in either direction → reject by default.
    # Better to miss a borderline item than dilute the briefing.
    return False, "off_topic", "no Tier 1/2 keyword match"


# Public API kept for backward compatibility
def is_relevant_for_fintech(title, full_text):
    return classify(title, full_text)[0]


def filter_all_pending():
    """
    Reads rows where is_relevant is NULL, classifies them, updates the column.
    Prints a tier breakdown so you can see what got through and what was rejected.
    Returns (relevant_count, irrelevant_count).
    """
    client = get_client()
    result = (
        client.table("regulation_updates")
        .select("id, title, full_text, source")
        .is_("is_relevant", "null")
        .execute()
    )
    rows = result.data or []
    if not rows:
        print("No unclassified regulation rows.")
        return (0, 0)

    print(f"\nClassifying {len(rows)} regulations...")

    tier_counts = {"tier_1": 0, "tier_2": 0, "tier_3_noise": 0, "off_topic": 0}
    relevant, irrelevant = 0, 0

    for row in rows:
        is_rel, tier, reason = classify(row.get("title"), row.get("full_text"))
        tier_counts[tier] += 1
        client.table("regulation_updates").update(
            {"is_relevant": is_rel}
        ).eq("id", row["id"]).execute()
        if is_rel:
            relevant += 1
        else:
            irrelevant += 1

    print(f"✅ Classification breakdown:")
    print(f"   Tier 1 (direct compliance):   {tier_counts['tier_1']}")
    print(f"   Tier 2 (indirect/supply chain):{tier_counts['tier_2']}")
    print(f"   Tier 3 (procedural noise):    {tier_counts['tier_3_noise']}")
    print(f"   Off-topic:                    {tier_counts['off_topic']}")
    print(f"   → {relevant} kept, {irrelevant} rejected")
    return relevant, irrelevant


if __name__ == "__main__":
    filter_all_pending()
