"""ReliefWeb — official public API (https://apidoc.reliefweb.int/).

Pulls recent consultancy/job postings matching NCE's service keywords.
These postings are strong buying signals: an organisation actively looking
for M&E / data collection / analytics capacity right now.
"""
import requests

NAME = "ReliefWeb consultancies"
DESCRIPTION = ("Official ReliefWeb API — recent M&E, survey, data-collection and "
               "analytics consultancy postings from NGOs and UN agencies.")
NEEDS = []

API = "https://api.reliefweb.int/v2/jobs"
DEFAULT_QUERY = ('"monitoring and evaluation" OR "baseline survey" OR '
                 '"data collection" OR "data analyst" OR "M&E" OR dashboard')


def pull(settings: dict) -> list[dict]:
    query = settings.get("reliefweb_query") or DEFAULT_QUERY
    params = {
        "appname": settings.get("reliefweb_appname") or "nce-lead-crm",
        "query[value]": query,
        "query[operator]": "OR",
        "limit": 30,
        "sort[]": "date:desc",
        "fields[include][]": ["title", "source.name", "country.name",
                              "date.created", "url", "career_categories.name"],
    }
    resp = requests.get(API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    leads = []
    for item in data.get("data", []):
        f = item.get("fields", {})
        org = ""
        srcs = f.get("source") or []
        if isinstance(srcs, list) and srcs:
            org = srcs[0].get("name", "")
        elif isinstance(srcs, dict):
            org = srcs.get("name", "")
        countries = f.get("country") or []
        country = countries[0].get("name", "") if countries else ""
        title = f.get("title", "")
        posted = (f.get("date", {}) or {}).get("created", "")[:10]
        if not org:
            continue
        leads.append({
            "org": org,
            "country": country,
            "trigger": f"your recent posting: \"{title}\"",
            "notes": f"ReliefWeb posting: {title}",
            "url": f.get("url", ""),
            "source": "ReliefWeb",
            "posted_date": posted,
            "dedupe_key": f"rw|{item.get('id')}",
        })
    return leads
