"""Enrichment & scoring for incoming leads.

Every raw lead pulled by a source module passes through enrich() before it is
inserted into the pipeline. This assigns:
  - segment        (which NCE service line it maps to)
  - score 0-100    (fit + signal strength + region + recency)
  - tentative_value (rough engagement value in USD, based on segment norms)
"""
from __future__ import annotations
import datetime
import json

from services_catalog import SERVICES, active_keys

# How much we trust each source as a *buying signal*.
SOURCE_WEIGHT = {
    "ReliefWeb": 30,       # live consultancy/tender postings = active demand
    "World Bank": 25,      # funded active projects = budget exists
    "World Bank Tenders": 32,  # open tender w/ deadline + named contact = strongest signal
    "ZPPA": 28,            # open government tender = active, budgeted demand
    "Grants.gov": 26,      # open US federal funding opportunity w/ deadline
    "TED (EU)": 30,        # open EU public tender w/ deadline, often named contact
    "SAM.gov": 26,         # open US federal contract solicitation w/ deadline
    "SADC": 29,            # open regional tender w/ deadline + named contact
    "eTenders SA": 27,     # open SA government tender w/ deadline + named contact
    "GoZambiaJobs": 14,    # hiring signal only, no explicit budget/tender attached
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


# Universal "someone is actively buying, right now" signals — deliberately
# service-agnostic (topical fit is already scored separately via SERVICES
# keywords), so these apply the same demand-signal boost whether the lead is
# a software tender, a call-center RFP, or an insurance-platform bid.
HOT_KEYWORDS = [
    "request for proposal", "request for quotation", "invitation to bid",
    "expression of interest", "call for proposals", "consultan", "rfp", "rfq",
    "tender", "solicitation", "appointment of a service provider",
    "appointment of a consultant", "procurement of",
]

# Hits needed against the winning service's keyword list to count as "fully
# aligned" (100%) — calibrated against short raw-lead text (titles/summaries
# rarely contain more than a handful of on-topic phrases).
ALIGNMENT_CAP = 4


NAME_TO_KEY = {v["name"]: k for k, v in SERVICES.items()}


def classify_segment(text: str, keys: list[str] | None = None) -> tuple[str, int]:
    """Return (best service key, keyword hit count) among the given (or all) services."""
    text = text.lower()
    keys = keys or list(SERVICES.keys())
    best, best_hits = (keys[0] if keys else next(iter(SERVICES))), 0
    for key in keys:
        svc = SERVICES.get(key)
        if not svc:
            continue
        hits = sum(1 for kw in svc["keywords"] if kw in text)
        if hits > best_hits:
            best, best_hits = key, hits
    return best, best_hits


def score_lead(raw: dict, settings: dict | None = None) -> dict:
    """Take a raw lead dict from a source and return an enriched lead dict.

    `settings` (if given) supplies `active_services` — the subset of NCE's 12
    service lines currently in scope, restricting which one a lead can be
    classified into. Also attaches `score_breakdown` (a JSON list of
    {label, points} the score was built from) and `value_note` (a one-line
    explanation of the tentative value) so the UI can show its work instead
    of presenting a bare number.
    """
    blob = " ".join(str(raw.get(k, "")) for k in
                    ("org", "trigger", "notes", "role", "how_to_apply")).lower()

    keys = active_keys(settings or {})
    seg_key = NAME_TO_KEY.get(raw.get("segment") or "")
    if seg_key and seg_key in keys:
        hits = sum(1 for kw in SERVICES[seg_key]["keywords"] if kw in blob)
    else:
        seg_key, hits = classify_segment(blob, keys)
    segment = SERVICES[seg_key]["name"]

    breakdown = []
    source = raw.get("source") or "unknown"
    base = SOURCE_WEIGHT.get(raw.get("source", ""), 15)
    score = base
    breakdown.append({"label": f"Source signal ({source})", "points": base})

    fit_pts = min(hits * 8, 32)
    score += fit_pts
    if fit_pts:
        breakdown.append({"label": f"Topical fit ({hits} keyword match{'es' if hits != 1 else ''})",
                           "points": fit_pts})

    hot_hits = sum(1 for kw in HOT_KEYWORDS if kw in blob)
    hot_pts = hot_hits * 6
    score += hot_pts
    if hot_pts:
        breakdown.append({"label": f"Demand signals ({hot_hits} hot keyword{'s' if hot_hits != 1 else ''})",
                           "points": hot_pts})

    country = str(raw.get("country", "")).lower()
    if any(c in country for c in PRIORITY_COUNTRIES):
        score += 12                                              # regional advantage
        breakdown.append({"label": "Priority region", "points": 12})

    if raw.get("email"):
        score += 8                                               # reachable now
        breakdown.append({"label": "Contact email available", "points": 8})

    posted = raw.get("posted_date")
    if posted:
        try:
            age = (datetime.date.today() -
                   datetime.date.fromisoformat(str(posted)[:10])).days
            if age <= 7:
                score += 10
                breakdown.append({"label": "Posted within 7 days", "points": 10})
            elif age <= 30:
                score += 5
                breakdown.append({"label": "Posted within 30 days", "points": 5})
        except ValueError:
            pass

    clamped = max(5, min(100, score))
    if clamped != score:
        breakdown.append({"label": "Clamped to 5-100 range", "points": clamped - score})
    score = clamped

    lo, hi = SERVICES[seg_key]["value_range"]
    tentative = int(lo + (hi - lo) * (score / 100))
    alignment_pct = round(min(hits, ALIGNMENT_CAP) / ALIGNMENT_CAP * 100)

    lead = dict(raw)
    lead["segment"] = segment
    lead["score"] = score
    lead["alignment_pct"] = alignment_pct
    lead["tentative_value"] = tentative
    lead["score_breakdown"] = json.dumps(breakdown)
    lead["value_note"] = (
        f"{segment} deals typically run ${lo:,}-${hi:,}; a fit score of {score}/100 "
        f"places this one at ${tentative:,}. Alignment with what we offer: {alignment_pct}% "
        f"({hits} matching signal{'s' if hits != 1 else ''} for this service)."
    )
    lead.setdefault("stage", "New")
    return lead
