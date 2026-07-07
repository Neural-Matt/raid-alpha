"""SAM.gov — official US federal contract opportunities API (requires a free key).

Get a free key: log into sam.gov (or create an account) -> Account Details ->
Request a public API key. Distinct from Grants.gov (which covers *assistance/
grant* funding) — SAM.gov covers federal *contract* opportunities (solicitations,
RFPs/RFQs), including USAID and State Department-issued procurements that
often fund M&E, data collection and digital-modernisation work with
international delivery.

Note: this module is built to SAM.gov's documented request/response shape but
has not been live-tested end-to-end (doing so needs a real account-issued key,
which only the CRM's own user can obtain). Report back if the shape has
drifted and it needs a fix.
"""
import datetime

import requests

NAME = "SAM.gov (US federal contracts)"
DESCRIPTION = ("Official US federal contract-opportunities API — solicitations and "
               "RFPs/RFQs matching your keyword, including USAID/State Dept "
               "procurements. Requires a free SAM.gov API key.")
NEEDS = ["sam_gov_api_key"]

API = "https://api.sam.gov/opportunities/v2/search"
DEFAULT_QUERY = "monitoring and evaluation"
MAX_LEADS = 20


def pull(settings: dict) -> list[dict]:
    key = settings.get("sam_gov_api_key", "").strip()
    if not key:
        raise RuntimeError("Add your SAM.gov API key in Settings first.")
    query = settings.get("sam_gov_query") or DEFAULT_QUERY
    days_back = int(settings.get("sam_gov_days_back") or 30)

    today = datetime.date.today()
    posted_from = (today - datetime.timedelta(days=days_back)).strftime("%m/%d/%Y")
    posted_to = today.strftime("%m/%d/%Y")

    resp = requests.get(API, params={
        "api_key": key,
        "title": query,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "limit": MAX_LEADS,
        "ptype": "o",  # solicitations (open opportunities)
    }, timeout=30)
    resp.raise_for_status()
    hits = resp.json().get("opportunitiesData", []) or []

    leads = []
    for o in hits[:MAX_LEADS]:
        org = o.get("fullParentPathName") or o.get("departmentName") or ""
        if not org:
            continue
        contact = (o.get("pointOfContact") or [{}])[0]
        title = o.get("title", "")
        leads.append({
            "org": org.split(".")[-1][:160] if "." in org else org[:160],
            "contact": contact.get("fullName", ""),
            "email": contact.get("email", ""),
            "phone": contact.get("phone", ""),
            "role": contact.get("title", "") or "Contracting contact",
            "country": "United States",
            "trigger": f"their open federal solicitation: \"{title[:120]}\"",
            "notes": f"SAM.gov opportunity {o.get('solicitationNumber','')} from {org}.",
            "how_to_apply": (o.get("description") or "")[:2000],
            "deadline": (o.get("responseDeadLine") or "")[:10],
            "url": o.get("uiLink", ""),
            "source": "SAM.gov",
            "posted_date": (o.get("postedDate") or "")[:10],
            "dedupe_key": f"samgov|{o.get('noticeId','')}",
        })
    return leads
