"""TED (Tenders Electronic Daily) — official EU public procurement API.

api.ted.europa.eu/v3/notices/search is free, public, and requires no API key
or registration. Publishes every high-value public contract notice across
the EU — a strong source for European institutions/agencies procuring
M&E, data, or digital-modernisation work with international bidders welcome.
"""
import datetime

import requests

NAME = "TED (EU public procurement)"
DESCRIPTION = ("Official EU Tenders Electronic Daily API — live European public "
               "procurement notices matching your keywords, with real deadlines.")
NEEDS = []

API = "https://api.ted.europa.eu/v3/notices/search"
DEFAULT_QUERY = "monitoring and evaluation"
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
    days_back = int(settings.get("ted_days_back") or 60)
    resp = requests.post(API, json={
        # search description text (titles are mostly generic CPV category
        # names — the real detail, and our best recall, is in the description)
        "query": f'description-lot ~ "{query}" AND publication-date >= today(-{days_back})',
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
