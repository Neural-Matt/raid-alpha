"""TED (Tenders Electronic Daily) — official EU public procurement API.

api.ted.europa.eu/v3/notices/search is free, public, and requires no API key
or registration. Publishes every high-value public contract notice across
the EU — a strong source for European institutions/agencies procuring across
NCE's 12 service lines, with international bidders welcome.

TED's expert query syntax supports parenthesized OR-chains of `description-lot
~ "phrase"` clauses (verified live) — so the default query below searches for
any of several representative phrases at once rather than a single term.
"""
import datetime

import requests

NAME = "TED (EU public procurement)"
DESCRIPTION = ("Official EU Tenders Electronic Daily API — live European public "
               "procurement notices matching NCE's service keywords, with real deadlines.")
NEEDS = []

API = "https://api.ted.europa.eu/v3/notices/search"
# a curated, representative slice of the full catalog — TED's query has a
# practical length limit, so this isn't the whole 250-keyword list
_DEFAULT_TERMS = [
    "monitoring and evaluation", "data analysis", "business intelligence",
    "software development", "artificial intelligence", "cloud migration",
    "digital transformation", "call center", "network design", "web application development",
    "mobile app development", "capacity building", "health information system",
    "insurance", "process automation",
]
DEFAULT_QUERY = ",".join(_DEFAULT_TERMS)
FIELDS = ["notice-title", "buyer-name", "buyer-country", "publication-number",
          "publication-date", "deadline-receipt-tender-date-lot", "description-lot"]
MAX_LEADS = 20


def _first(value):
    """TED often wraps values in language-dict-of-list or plain list shapes.
    Prefers English text when a notice is published in multiple languages."""
    if isinstance(value, dict):
        value = value.get("eng") or next(iter(value.values()), None)
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def pull(settings: dict) -> list[dict]:
    query = settings.get("ted_query") or DEFAULT_QUERY
    terms = [t.strip() for t in query.split(",") if t.strip()]
    days_back = int(settings.get("ted_days_back") or 60)
    # search description text (titles are mostly generic CPV category names —
    # the real detail, and our best recall, is in the description); chain
    # every configured term with OR so any one match qualifies the notice
    or_clause = " OR ".join(f'description-lot ~ "{t}"' for t in terms)
    resp = requests.post(API, json={
        "query": f'({or_clause}) AND publication-date >= today(-{days_back})',
        "fields": FIELDS,
        "limit": MAX_LEADS,
        "scope": "ALL",
    }, timeout=30)
    resp.raise_for_status()
    notices = resp.json().get("notices", []) or []

    today = datetime.date.today().isoformat()
    leads = []
    for n in notices:
        org = _first(n.get("buyer-name"))
        if not org:
            continue
        title = _first(n.get("notice-title"))
        deadline = _first(n.get("deadline-receipt-tender-date-lot"))[:10]
        if deadline and deadline < today:
            continue  # skip only if a deadline is present AND has passed
        desc = _first(n.get("description-lot"))
        pub_no = n.get("publication-number", "")
        leads.append({
            "org": str(org)[:160],
            "country": str(_first(n.get("buyer-country"))),
            "trigger": f"their open EU tender: \"{title[:120]}\"",
            "notes": f"TED notice {pub_no}: {title}",
            "how_to_apply": str(desc)[:2000],
            "deadline": deadline,
            "url": f"https://ted.europa.eu/en/notice/{pub_no}/html",
            "source": "TED (EU)",
            "posted_date": str(n.get("publication-date", ""))[:10],
            "dedupe_key": f"ted|{pub_no}",
        })
    return leads
