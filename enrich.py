"""Enrichment & scoring for incoming leads.

Every raw lead pulled by a source module passes through enrich() before it is
inserted into the pipeline. This assigns:
  - segment        (which NCE service line it maps to)
  - score 0-100    (fit + signal strength + region + recency)
  - tentative_value (rough engagement value in USD, based on segment norms)
"""
from __future__ import annotations
import datetime

SEGMENT_KEYWORDS = {
    "NGO / Donor (M&E, data collection)": [
        "m&e", "monitoring and evaluation", "baseline", "endline", "survey",
        "data collection", "enumerat", "kobo", "odk", "surveycto", "evaluation",
        "impact assessment", "household survey", "field research", "humanitarian",
    ],
    "Financial services (BI, reporting)": [
        "bank", "microfinance", "insurance", "fintech", "regulatory reporting",
        "financial reporting", "credit", "lending",
    ],
    "Corporate (analytics, automation)": [
        "dashboard", "business intelligence", "power bi", "tableau", "analytics",
        "kpi", "automation", "rpa", "reporting",
    ],
    "Public sector": [
        "ministry", "government", "public sector", "statistics office", "census",
        "national statistic", "e-government",
    ],
    "Migration / modernization": [
        "migration", "legacy", "modernization", "modernisation", "cloud migration",
        "database", "system integration", "erp",
    ],
    "Training & capacity building": [
        "training", "capacity building", "workshop", "upskill", "data literacy",
        "curriculum",
    ],
    "Platform / product": [
        "platform", "portal", "mis ", "management information system", "web application",
        "data system",
    ],
}

# Typical engagement value range per segment (USD) — used for tentative pipeline value.
SEGMENT_VALUE = {
    "NGO / Donor (M&E, data collection)": (15000, 80000),
    "Financial services (BI, reporting)": (10000, 60000),
    "Corporate (analytics, automation)": (8000, 45000),
    "Public sector": (20000, 120000),
    "Migration / modernization": (12000, 70000),
    "Training & capacity building": (3000, 20000),
    "Platform / product": (25000, 150000),
}

# How much we trust each source as a *buying signal*.
SOURCE_WEIGHT = {
    "ReliefWeb": 30,       # live consultancy/tender postings = active demand
    "World Bank": 25,      # funded active projects = budget exists
    "ZPPA": 28,            # open government tender = active, budgeted demand
    "RSS feed": 20,
    "Apollo": 15,          # contact data, no explicit demand signal
    "Hunter": 12,
    "Manual": 15,
}

PRIORITY_COUNTRIES = [
    "zambia", "zimbabwe", "malawi", "tanzania", "kenya", "uganda", "rwanda",
    "mozambique", "botswana", "namibia", "south africa", "drc", "congo",
    "ethiopia", "ghana", "nigeria",
]

HOT_KEYWORDS = [
    "baseline", "endline", "consultan", "rfp", "request for proposal", "tender",
    "evaluation", "data collection", "dashboard", "m&e", "survey firm",
]


def classify_segment(text: str) -> tuple[str, int]:
    """Return (best segment, keyword hit count)."""
    text = text.lower()
    best, best_hits = "Corporate (analytics, automation)", 0
    for segment, kws in SEGMENT_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in text)
        if hits > best_hits:
            best, best_hits = segment, hits
    return best, best_hits


def score_lead(raw: dict) -> dict:
    """Take a raw lead dict from a source and return an enriched lead dict."""
    blob = " ".join(str(raw.get(k, "")) for k in
                    ("org", "trigger", "notes", "role", "segment")).lower()

    segment = raw.get("segment") or ""
    if segment:
        hits = sum(1 for kw in SEGMENT_KEYWORDS.get(segment, []) if kw in blob)
    else:
        segment, hits = classify_segment(blob)

    score = SOURCE_WEIGHT.get(raw.get("source", ""), 15)
    score += min(hits * 8, 32)                                   # topical fit
    score += sum(6 for kw in HOT_KEYWORDS if kw in blob)         # demand signals
    country = str(raw.get("country", "")).lower()
    if any(c in country for c in PRIORITY_COUNTRIES):
        score += 12                                              # regional advantage
    if raw.get("email"):
        score += 8                                               # reachable now
    posted = raw.get("posted_date")
    if posted:
        try:
            age = (datetime.date.today() -
                   datetime.date.fromisoformat(str(posted)[:10])).days
            if age <= 7:
                score += 10
            elif age <= 30:
                score += 5
        except ValueError:
            pass
    score = max(5, min(100, score))

    lo, hi = SEGMENT_VALUE.get(segment, (8000, 40000))
    tentative = int(lo + (hi - lo) * (score / 100))

    lead = dict(raw)
    lead["segment"] = segment
    lead["score"] = score
    lead["tentative_value"] = tentative
    lead.setdefault("stage", "New")
    return lead
